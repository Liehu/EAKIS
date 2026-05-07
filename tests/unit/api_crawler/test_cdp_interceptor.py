from __future__ import annotations

import pytest

from src.api_crawler.agents.cdp_interceptor import CDPAgent, _traffic_to_raw
from src.api_crawler.models import (
    CDPTrafficItem,
    CrawlMethod,
    ProtocolType,
    SSEEvent,
    WSFrame,
)
from src.api_crawler.services.base import BaseCDPClient
from src.api_crawler.services.stub_browser import StubCDPClient


class FakeCDPClient(BaseCDPClient):
    def __init__(self, items: list[CDPTrafficItem]) -> None:
        self._items = items

    async def capture_traffic(self, url: str) -> list[CDPTrafficItem]:
        return self._items

    async def capture_batch(self, urls: list[str]) -> list[CDPTrafficItem]:
        return self._items


@pytest.fixture
def stub_client() -> StubCDPClient:
    return StubCDPClient()


@pytest.fixture
def agent(stub_client: StubCDPClient) -> CDPAgent:
    return CDPAgent(client=stub_client)


# --- Model tests ---


class TestCDPModels:
    def test_ws_frame_defaults(self):
        frame = WSFrame(direction="sent", payload="hello")
        assert frame.direction == "sent"
        assert frame.opcode == 1
        assert frame.timestamp is None

    def test_sse_event_defaults(self):
        event = SSEEvent(url="https://example.com/events")
        assert event.event_type is None
        assert event.data == ""
        assert event.event_id is None

    def test_traffic_item_defaults(self):
        item = CDPTrafficItem(url="https://example.com/api")
        assert item.protocol == ProtocolType.HTTP
        assert item.ws_frames == []
        assert item.sse_events == []
        assert item.status_code is None


# --- StubCDPClient tests ---


class TestStubCDPClient:
    @pytest.mark.asyncio
    async def test_capture_traffic_returns_all_protocols(self, stub_client: StubCDPClient):
        items = await stub_client.capture_traffic("https://example.com")
        protocols = {item.protocol for item in items}
        assert ProtocolType.WEBSOCKET in protocols
        assert ProtocolType.SSE in protocols
        assert ProtocolType.GRPC_WEB in protocols

    @pytest.mark.asyncio
    async def test_capture_traffic_websocket_has_frames(self, stub_client: StubCDPClient):
        items = await stub_client.capture_traffic("https://example.com")
        ws = next(i for i in items if i.protocol == ProtocolType.WEBSOCKET)
        assert len(ws.ws_frames) == 2
        assert ws.ws_frames[0].direction == "received"
        assert ws.ws_frames[1].direction == "sent"

    @pytest.mark.asyncio
    async def test_capture_batch_flattens_results(self, stub_client: StubCDPClient):
        items = await stub_client.capture_batch(["https://a.com", "https://b.com"])
        assert len(items) == 6  # 3 per URL


# --- CDPAgent tests ---


class TestCDPAgent:
    @pytest.mark.asyncio
    async def test_capture_converts_to_raw_interfaces(self, agent: CDPAgent):
        results = await agent.capture(["https://example.com"], already_captured=[])
        assert len(results) > 0
        for r in results:
            assert r.crawl_method == CrawlMethod.CDP

    @pytest.mark.asyncio
    async def test_capture_deduplicates(self, agent: CDPAgent):
        results = await agent.capture(
            ["https://example.com"],
            already_captured=["GET:/ws/notifications"],
        )
        paths = [r.path for r in results]
        assert "/ws/notifications" not in paths

    @pytest.mark.asyncio
    async def test_capture_detailed_returns_traffic_items(self, agent: CDPAgent):
        results = await agent.capture_detailed(
            ["https://example.com"], already_captured=[]
        )
        assert all(isinstance(r, CDPTrafficItem) for r in results)

    @pytest.mark.asyncio
    async def test_capture_skips_already_captured(self, agent: CDPAgent):
        all_items = await agent.capture_detailed(
            ["https://example.com"], already_captured=[]
        )
        from urllib.parse import urlparse

        first_item = all_items[0]
        first_path = urlparse(first_item.url).path
        deduped = await agent.capture_detailed(
            ["https://example.com"],
            already_captured=[f"{first_item.method}:{first_path}"],
        )
        assert all(r.url != first_item.url for r in deduped)


# --- _traffic_to_raw conversion tests ---


class TestTrafficToRaw:
    def test_http_traffic(self):
        item = CDPTrafficItem(
            url="https://example.com/api/v1/users",
            method="GET",
            protocol=ProtocolType.HTTP,
            headers={"Accept": "application/json"},
        )
        raw = _traffic_to_raw(item)
        assert raw is not None
        assert raw.path == "/api/v1/users"
        assert raw.method == "GET"
        assert raw.crawl_method == CrawlMethod.CDP
        assert "CDP HTTP capture" in (raw.trigger_scenario or "")

    def test_websocket_traffic(self):
        item = CDPTrafficItem(
            url="wss://example.com/ws/chat",
            protocol=ProtocolType.WEBSOCKET,
            ws_frames=[
                WSFrame(direction="sent", payload="hello"),
                WSFrame(direction="received", payload="world"),
            ],
        )
        raw = _traffic_to_raw(item)
        assert raw is not None
        assert raw.method == "GET"
        assert "WebSocket" in (raw.trigger_scenario or "")
        assert "2 frames" in (raw.trigger_scenario or "")

    def test_sse_traffic(self):
        item = CDPTrafficItem(
            url="https://example.com/events",
            protocol=ProtocolType.SSE,
            sse_events=[
                SSEEvent(url="https://example.com/events", data="ping"),
                SSEEvent(url="https://example.com/events", data="pong"),
            ],
        )
        raw = _traffic_to_raw(item)
        assert raw is not None
        assert "SSE" in (raw.trigger_scenario or "")
        assert "2 events" in (raw.trigger_scenario or "")

    def test_grpc_web_traffic(self):
        item = CDPTrafficItem(
            url="https://example.com/api/grpc.UserService/GetProfile",
            method="POST",
            protocol=ProtocolType.GRPC_WEB,
            headers={"Content-Type": "application/grpc-web+proto"},
        )
        raw = _traffic_to_raw(item)
        assert raw is not None
        assert raw.method == "POST"
        assert "gRPC-Web" in (raw.trigger_scenario or "")


# --- FakeCDPClient tests ( verifies agent works with arbitrary traffic ) ---


class TestCDPAgentWithFakeClient:
    @pytest.mark.asyncio
    async def test_agent_handles_empty_traffic(self):
        fake = FakeCDPClient(items=[])
        agent = CDPAgent(client=fake)
        results = await agent.capture(["https://example.com"], already_captured=[])
        assert results == []

    @pytest.mark.asyncio
    async def test_agent_handles_mixed_protocols(self):
        items = [
            CDPTrafficItem(
                url="https://example.com/api/v1/data",
                method="GET",
                protocol=ProtocolType.HTTP,
            ),
            CDPTrafficItem(
                url="wss://example.com/ws",
                protocol=ProtocolType.WEBSOCKET,
            ),
            CDPTrafficItem(
                url="https://example.com/sse",
                protocol=ProtocolType.SSE,
            ),
            CDPTrafficItem(
                url="https://example.com/grpc.Service/Method",
                method="POST",
                protocol=ProtocolType.GRPC_WEB,
            ),
        ]
        fake = FakeCDPClient(items=items)
        agent = CDPAgent(client=fake)
        results = await agent.capture(["https://example.com"], already_captured=[])
        assert len(results) == 4
        methods = {r.method for r in results}
        assert "GET" in methods
        assert "POST" in methods

    @pytest.mark.asyncio
    async def test_agent_deduplicates_across_batch(self):
        items = [
            CDPTrafficItem(
                url="https://example.com/api/v1/data",
                method="GET",
                protocol=ProtocolType.HTTP,
            ),
            CDPTrafficItem(
                url="https://example.com/api/v1/data",
                method="GET",
                protocol=ProtocolType.HTTP,
            ),
        ]
        fake = FakeCDPClient(items=items)
        agent = CDPAgent(client=fake)
        results = await agent.capture(["https://example.com"], already_captured=[])
        assert len(results) == 1


# --- PlaywrightCDPClient _build_results tests (unit-level, no browser) ---


class TestBuildResults:
    def test_builds_http_from_js_captured(self):
        from src.api_crawler.services.playwright_cdp import PlaywrightCDPClient

        client = PlaywrightCDPClient()
        js_captured = [
            {
                "protocol": "http",
                "url": "https://example.com/api/v1/users",
                "method": "GET",
                "headers": {"Accept": "application/json"},
                "body": None,
                "resourceType": "Fetch",
                "timestamp": "2026-05-07T10:00:00Z",
            }
        ]
        results = client._build_results(js_captured, {}, {})
        assert len(results) == 1
        assert results[0].protocol == ProtocolType.HTTP
        assert results[0].method == "GET"
        assert results[0].url == "https://example.com/api/v1/users"

    def test_builds_websocket_from_js_captured(self):
        from src.api_crawler.services.playwright_cdp import PlaywrightCDPClient

        client = PlaywrightCDPClient()
        js_captured = [
            {
                "protocol": "websocket",
                "url": "wss://example.com/ws/chat",
                "method": "GET",
                "headers": {},
                "resourceType": "WebSocket",
                "timestamp": "2026-05-07T10:00:00Z",
            },
            {
                "protocol": "ws_frame",
                "url": "wss://example.com/ws/chat",
                "method": "RECV",
                "body": '{"msg":"hello"}',
                "timestamp": "2026-05-07T10:00:01Z",
            },
            {
                "protocol": "ws_frame",
                "url": "wss://example.com/ws/chat",
                "method": "SEND",
                "body": '{"msg":"world"}',
                "timestamp": "2026-05-07T10:00:02Z",
            },
        ]
        results = client._build_results(js_captured, {}, {})
        assert len(results) == 1
        ws = results[0]
        assert ws.protocol == ProtocolType.WEBSOCKET
        assert len(ws.ws_frames) == 2
        assert ws.ws_frames[0].direction == "received"
        assert ws.ws_frames[1].direction == "sent"

    def test_builds_sse_from_js_captured(self):
        from src.api_crawler.services.playwright_cdp import PlaywrightCDPClient

        client = PlaywrightCDPClient()
        js_captured = [
            {
                "protocol": "sse",
                "url": "https://example.com/events",
                "method": "GET",
                "headers": {},
                "resourceType": "EventSource",
                "timestamp": "2026-05-07T10:00:00Z",
            },
            {
                "protocol": "sse_event",
                "url": "https://example.com/events",
                "method": "EVENT",
                "body": "data: update",
                "eventType": "message",
                "lastEventId": "42",
                "timestamp": "2026-05-07T10:00:01Z",
            },
        ]
        results = client._build_results(js_captured, {}, {})
        assert len(results) == 1
        sse = results[0]
        assert sse.protocol == ProtocolType.SSE
        assert len(sse.sse_events) == 1
        assert sse.sse_events[0].event_type == "message"
        assert sse.sse_events[0].event_id == "42"

    def test_detects_grpc_web_from_content_type(self):
        from src.api_crawler.services.playwright_cdp import PlaywrightCDPClient

        client = PlaywrightCDPClient()
        js_captured = [
            {
                "protocol": "http",
                "url": "https://example.com/grpc.UserService/Get",
                "method": "POST",
                "headers": {"Content-Type": "application/grpc-web+proto"},
                "body": None,
                "resourceType": "Fetch",
                "timestamp": "2026-05-07T10:00:00Z",
            }
        ]
        results = client._build_results(js_captured, {}, {})
        assert results[0].protocol == ProtocolType.GRPC_WEB

    def test_merges_cdp_network_requests(self):
        from src.api_crawler.services.playwright_cdp import PlaywrightCDPClient

        client = PlaywrightCDPClient()
        js_captured = [
            {
                "protocol": "http",
                "url": "https://example.com/api/v1/users",
                "method": "GET",
                "headers": {},
                "resourceType": "Fetch",
                "timestamp": "2026-05-07T10:00:00Z",
            }
        ]
        network_requests = {
            "req-001": {
                "url": "https://example.com/api/v1/users",
                "method": "GET",
                "headers": {},
                "resource_type": "Fetch",
                "request_id": "req-001",
                "status_code": 200,
            }
        }
        results = client._build_results(js_captured, network_requests, {})
        assert results[0].status_code == 200
        assert results[0].request_id == "req-001"

    def test_merges_cdp_ws_sessions(self):
        from src.api_crawler.services.playwright_cdp import PlaywrightCDPClient

        client = PlaywrightCDPClient()
        ws_sessions = {
            "ws-001": {
                "url": "wss://example.com/ws/live",
                "frames_sent": [{"payload": '{"a":1}', "opcode": 1, "timestamp": 0}],
                "frames_received": [{"payload": '{"b":2}', "opcode": 1, "timestamp": 1}],
            }
        }
        results = client._build_results([], {}, ws_sessions)
        assert len(results) == 1
        assert results[0].protocol == ProtocolType.WEBSOCKET
        assert len(results[0].ws_frames) == 2

    def test_deduplicates_http_by_method_and_url(self):
        from src.api_crawler.services.playwright_cdp import PlaywrightCDPClient

        client = PlaywrightCDPClient()
        js_captured = [
            {
                "protocol": "http",
                "url": "https://example.com/api/v1/data",
                "method": "GET",
                "headers": {},
                "resourceType": "Fetch",
                "timestamp": "2026-05-07T10:00:00Z",
            },
            {
                "protocol": "http",
                "url": "https://example.com/api/v1/data",
                "method": "GET",
                "headers": {},
                "resourceType": "Fetch",
                "timestamp": "2026-05-07T10:00:01Z",
            },
        ]
        results = client._build_results(js_captured, {}, {})
        assert len(results) == 1

    def test_empty_input(self):
        from src.api_crawler.services.playwright_cdp import PlaywrightCDPClient

        client = PlaywrightCDPClient()
        results = client._build_results([], {}, {})
        assert results == []
