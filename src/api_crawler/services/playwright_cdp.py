from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from src.api_crawler.models import CDPTrafficItem, ProtocolType, SSEEvent, WSFrame
from src.api_crawler.services.base import BaseCDPClient

logger = logging.getLogger("eakis.api_crawler.cdp")

_JS_INTERCEPT_SCRIPT = r"""
(function() {
  if (window.__cdp_hooks_installed) return;
  window.__cdp_hooks_installed = true;
  window.__cdp_captured = [];

  // --- fetch interception ---
  var _fetch = window.fetch;
  window.fetch = function(input, init) {
    var url = typeof input === 'string' ? input : (input && input.url ? input.url : String(input));
    var method = ((init && init.method) || 'GET').toUpperCase();
    var headers = {};
    if (init && init.headers) {
      if (typeof init.headers.forEach === 'function') {
        init.headers.forEach(function(v, k) { headers[k] = v; });
      } else {
        headers = Object.assign({}, init.headers);
      }
    }
    var body = (init && init.body != null) ? String(init.body) : null;
    window.__cdp_captured.push({
      protocol: 'http', url: url, method: method,
      headers: headers, body: body, resourceType: 'Fetch',
      timestamp: new Date().toISOString()
    });
    return _fetch.apply(this, arguments);
  };

  // --- XHR interception ---
  var _xhrOpen = XMLHttpRequest.prototype.open;
  var _xhrSend = XMLHttpRequest.prototype.send;
  var _xhrSetHeader = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.open = function(method, url) {
    this.__xhr = { method: method.toUpperCase(), url: String(url), headers: {} };
    return _xhrOpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.setRequestHeader = function(name, value) {
    if (this.__xhr) this.__xhr.headers[name] = value;
    return _xhrSetHeader.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function(body) {
    if (this.__xhr) {
      this.__xhr.body = body != null ? String(body) : null;
      window.__cdp_captured.push({
        protocol: 'http', url: this.__xhr.url, method: this.__xhr.method,
        headers: this.__xhr.headers, body: this.__xhr.body,
        resourceType: 'XHR', timestamp: new Date().toISOString()
      });
    }
    return _xhrSend.apply(this, arguments);
  };

  // --- WebSocket interception ---
  var _wsCtor = window.WebSocket;
  window.WebSocket = function(url, protocols) {
    var ws = protocols != null ? new _wsCtor(url, protocols) : new _wsCtor(url);
    window.__cdp_captured.push({
      protocol: 'websocket', url: url, method: 'GET',
      headers: {}, resourceType: 'WebSocket',
      timestamp: new Date().toISOString()
    });
    ws.addEventListener('message', function(ev) {
      window.__cdp_captured.push({
        protocol: 'ws_frame', url: url, method: 'RECV',
        body: typeof ev.data === 'string' ? ev.data : '[binary]',
        timestamp: new Date().toISOString()
      });
    });
    var _wsSend = ws.send.bind(ws);
    ws.send = function(data) {
      window.__cdp_captured.push({
        protocol: 'ws_frame', url: url, method: 'SEND',
        body: typeof data === 'string' ? data : '[binary]',
        timestamp: new Date().toISOString()
      });
      return _wsSend(data);
    };
    return ws;
  };
  window.WebSocket.prototype = _wsCtor.prototype;
  window.WebSocket.CONNECTING = _wsCtor.CONNECTING;
  window.WebSocket.OPEN = _wsCtor.OPEN;
  window.WebSocket.CLOSING = _wsCtor.CLOSING;
  window.WebSocket.CLOSED = _wsCtor.CLOSED;

  // --- EventSource (SSE) interception ---
  var _esCtor = window.EventSource;
  if (_esCtor) {
    window.EventSource = function(url, opts) {
      var es = new _esCtor(url, opts);
      window.__cdp_captured.push({
        protocol: 'sse', url: url, method: 'GET',
        headers: {}, resourceType: 'EventSource',
        timestamp: new Date().toISOString()
      });
      es.addEventListener('message', function(ev) {
        window.__cdp_captured.push({
          protocol: 'sse_event', url: url, method: 'EVENT',
          body: ev.data || '',
          eventType: ev.type || 'message',
          lastEventId: ev.lastEventId || null,
          timestamp: new Date().toISOString()
        });
      });
      return es;
    };
    window.EventSource.prototype = _esCtor.prototype;
    window.EventSource.CONNECTING = _esCtor.CONNECTING;
    window.EventSource.OPEN = _esCtor.OPEN;
    window.EventSource.CLOSED = _esCtor.CLOSED;
  }
})();
"""

_GRPC_CONTENT_TYPES = {
    "application/grpc",
    "application/grpc-web",
    "application/grpc-web-text",
    "application/grpc-web+proto",
    "application/grpc-web+json",
}


class PlaywrightCDPClient(BaseCDPClient):
    def __init__(self, max_buffer_mb: int = 50) -> None:
        self._max_buffer_bytes = max_buffer_mb * 1024 * 1024
        self._sessions: dict[int, dict[str, Any]] = {}

    async def capture_traffic(self, url: str) -> list[CDPTrafficItem]:
        page = await self._create_page()
        try:
            await self._inject_hooks(page)
            cdp = await self._init_cdp_session(page)

            network_requests: dict[str, dict[str, Any]] = {}
            ws_sessions: dict[str, dict[str, Any]] = {}

            self._register_cdp_handlers(cdp, network_requests, ws_sessions)

            await page.goto(url, wait_until="networkidle", timeout=30_000)
            await page.wait_for_timeout(3000)

            await self._scroll_page(page)

            js_captured = await page.evaluate("window.__cdp_captured || []")

            return self._build_results(
                js_captured, network_requests, ws_sessions
            )
        except Exception:
            logger.exception("CDP capture failed for %s", url)
            return []
        finally:
            await self._cleanup(page)

    async def capture_batch(self, urls: list[str]) -> list[CDPTrafficItem]:
        results: list[CDPTrafficItem] = []
        for url in urls:
            results.extend(await self.capture_traffic(url))
        return results

    async def _create_page(self) -> Any:
        try:
            from playwright.async_api import async_playwright

            pw = await async_playwright().start()
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            self._sessions[id(page)] = {"pw": pw, "browser": browser}
            return page
        except ImportError:
            raise RuntimeError(
                "playwright is required for CDP capture. "
                "Install with: pip install playwright && playwright install chromium"
            )

    async def _inject_hooks(self, page: Any) -> None:
        await page.add_init_script(_JS_INTERCEPT_SCRIPT)

    async def _init_cdp_session(self, page: Any) -> Any:
        context = page.context
        cdp = await context.new_cdp_session(page)
        await cdp.send(
            "Network.enable",
            {
                "maxResourceBufferSize": 10 * 1024 * 1024,
                "maxTotalBufferSize": self._max_buffer_bytes,
            },
        )
        await cdp.send(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": _JS_INTERCEPT_SCRIPT},
        )
        return cdp

    def _register_cdp_handlers(
        self,
        cdp: Any,
        network_requests: dict[str, dict[str, Any]],
        ws_sessions: dict[str, dict[str, Any]],
    ) -> None:
        def on_request(params: dict[str, Any]) -> None:
            rid = params.get("requestId", "")
            req = params.get("request", {})
            network_requests[rid] = {
                "url": req.get("url", ""),
                "method": req.get("method", "GET"),
                "headers": req.get("headers", {}),
                "resource_type": params.get("type", ""),
                "request_id": rid,
            }

        def on_response(params: dict[str, Any]) -> None:
            rid = params.get("requestId", "")
            if rid in network_requests:
                resp = params.get("response", {})
                network_requests[rid]["status_code"] = resp.get("status")

        def on_ws_created(params: dict[str, Any]) -> None:
            ws_sessions[params.get("requestId", "")] = {
                "url": params.get("url", ""),
                "frames_sent": [],
                "frames_received": [],
            }

        def on_ws_frame(params: dict[str, Any], direction: str) -> None:
            rid = params.get("requestId", "")
            if rid in ws_sessions:
                ws_sessions[rid][direction].append({
                    "payload": params.get("response", {}).get("payloadData", ""),
                    "timestamp": params.get("timestamp", 0),
                    "opcode": params.get("response", {}).get("opcode", 1),
                })

        cdp.on("Network.requestWillBeSent", on_request)
        cdp.on("Network.responseReceived", on_response)
        cdp.on("Network.webSocketCreated", on_ws_created)
        cdp.on(
            "Network.webSocketFrameSent",
            lambda p: on_ws_frame(p, "frames_sent"),
        )
        cdp.on(
            "Network.webSocketFrameReceived",
            lambda p: on_ws_frame(p, "frames_received"),
        )

    async def _scroll_page(self, page: Any) -> None:
        try:
            await page.evaluate(
                "async () => {"
                "  const delay = ms => new Promise(r => setTimeout(r, ms));"
                "  for (let i = 0; i < 5; i++) {"
                "    window.scrollBy(0, window.innerHeight);"
                "    await delay(500);"
                "  }"
                "  window.scrollTo(0, 0);"
                "}"
            )
        except Exception:
            pass

    def _build_results(
        self,
        js_captured: list[dict[str, Any]],
        network_requests: dict[str, dict[str, Any]],
        ws_sessions: dict[str, dict[str, Any]],
    ) -> list[CDPTrafficItem]:
        results: list[CDPTrafficItem] = []
        seen_urls: set[str] = set()

        for item in js_captured:
            proto = item.get("protocol", "http")
            url = item.get("url", "")

            if proto == "ws_frame":
                continue

            if proto == "sse_event":
                continue

            if proto == "websocket":
                if url not in seen_urls:
                    seen_urls.add(url)
                    frames = self._collect_ws_frames_for_url(url, js_captured)
                    results.append(CDPTrafficItem(
                        url=url,
                        method="GET",
                        protocol=ProtocolType.WEBSOCKET,
                        headers=item.get("headers", {}),
                        ws_frames=frames,
                        resource_type="WebSocket",
                        timestamp=item.get("timestamp"),
                    ))
                continue

            if proto == "sse":
                if url not in seen_urls:
                    seen_urls.add(url)
                    events = self._collect_sse_events_for_url(url, js_captured)
                    results.append(CDPTrafficItem(
                        url=url,
                        method="GET",
                        protocol=ProtocolType.SSE,
                        headers=item.get("headers", {}),
                        sse_events=events,
                        resource_type="EventSource",
                        timestamp=item.get("timestamp"),
                    ))
                continue

            # proto == 'http'
            method = item.get("method", "GET")
            headers = item.get("headers", {})
            body = item.get("body")
            resource_type = item.get("resourceType", "")
            key = f"{method}:{url}"
            if key in seen_urls:
                continue
            seen_urls.add(key)

            protocol = ProtocolType.HTTP
            ct = headers.get("Content-Type", headers.get("content-type", ""))
            if ct in _GRPC_CONTENT_TYPES:
                protocol = ProtocolType.GRPC_WEB

            cdp_info = self._match_cdp_request(
                url, method, network_requests
            )

            results.append(CDPTrafficItem(
                url=url,
                method=method,
                protocol=protocol,
                headers=headers,
                body=body,
                request_id=cdp_info.get("request_id"),
                resource_type=resource_type,
                status_code=cdp_info.get("status_code"),
                timestamp=item.get("timestamp"),
            ))

        for ws_id, ws_data in ws_sessions.items():
            ws_url = ws_data.get("url", "")
            if ws_url not in seen_urls:
                seen_urls.add(ws_url)
                frames = [
                    WSFrame(
                        direction="sent" if i < len(ws_data.get("frames_sent", [])) else "received",
                        payload=(ws_data.get("frames_sent", []) + ws_data.get("frames_received", []))[i].get("payload", ""),
                        opcode=(ws_data.get("frames_sent", []) + ws_data.get("frames_received", []))[i].get("opcode", 1),
                    )
                    for i in range(
                        len(ws_data.get("frames_sent", []))
                        + len(ws_data.get("frames_received", []))
                    )
                ]
                results.append(CDPTrafficItem(
                    url=ws_url,
                    method="GET",
                    protocol=ProtocolType.WEBSOCKET,
                    ws_frames=frames,
                    request_id=ws_id,
                    resource_type="WebSocket",
                ))

        return results

    @staticmethod
    def _collect_ws_frames_for_url(
        url: str, js_captured: list[dict[str, Any]]
    ) -> list[WSFrame]:
        frames: list[WSFrame] = []
        for item in js_captured:
            if item.get("protocol") != "ws_frame" or item.get("url") != url:
                continue
            direction = "received" if item.get("method") == "RECV" else "sent"
            frames.append(WSFrame(
                direction=direction,
                payload=item.get("body", ""),
                timestamp=item.get("timestamp"),
            ))
        return frames

    @staticmethod
    def _collect_sse_events_for_url(
        url: str, js_captured: list[dict[str, Any]]
    ) -> list[SSEEvent]:
        events: list[SSEEvent] = []
        for item in js_captured:
            if item.get("protocol") != "sse_event" or item.get("url") != url:
                continue
            events.append(SSEEvent(
                url=url,
                event_type=item.get("eventType", "message"),
                data=item.get("body", ""),
                event_id=item.get("lastEventId"),
                timestamp=item.get("timestamp"),
            ))
        return events

    @staticmethod
    def _match_cdp_request(
        url: str, method: str, network_requests: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        path = urlparse(url).path
        for info in network_requests.values():
            if info.get("method") == method and urlparse(info.get("url", "")).path == path:
                return info
        return {}

    async def _cleanup(self, page: Any) -> None:
        try:
            session = self._sessions.pop(id(page), {})
            browser = session.get("browser")
            pw = session.get("pw")
            if browser:
                await browser.close()
            if pw:
                await pw.stop()
        except Exception:
            pass
