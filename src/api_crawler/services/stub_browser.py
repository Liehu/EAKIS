from __future__ import annotations

from src.api_crawler.models import CDPTrafficItem, CapturedRequest, ProtocolType, WSFrame
from src.api_crawler.services.base import BaseBrowserClient, BaseCDPClient


class StubBrowserClient(BaseBrowserClient):
    async def navigate_and_interact(
        self,
        url: str,
        already_captured: list[str],
    ) -> list[CapturedRequest]:
        return [
            CapturedRequest(
                url=f"{url}/api/v1/dashboard",
                method="GET",
                headers={"Accept": "application/json"},
                source="dynamic",
            ),
            CapturedRequest(
                url=f"{url}/api/v1/user/profile",
                method="POST",
                headers={"Content-Type": "application/json"},
                body='{"action":"update"}',
                source="dynamic",
            ),
        ]


class StubCDPClient(BaseCDPClient):
    async def capture_traffic(self, url: str) -> list[CDPTrafficItem]:
        host = url.replace("https://", "").replace("http://", "")
        return [
            CDPTrafficItem(
                url=f"wss://{host}/ws/notifications",
                method="GET",
                protocol=ProtocolType.WEBSOCKET,
                headers={"Upgrade": "websocket"},
                ws_frames=[
                    WSFrame(direction="received", payload='{"type":"ping"}'),
                    WSFrame(direction="sent", payload='{"type":"pong"}'),
                ],
                resource_type="WebSocket",
            ),
            CDPTrafficItem(
                url=f"{url}/api/v1/stream/events",
                method="GET",
                protocol=ProtocolType.SSE,
                headers={"Accept": "text/event-stream"},
                resource_type="EventSource",
            ),
            CDPTrafficItem(
                url=f"{url}/api/grpc.UserService/GetProfile",
                method="POST",
                protocol=ProtocolType.GRPC_WEB,
                headers={"Content-Type": "application/grpc-web+proto"},
                resource_type="Fetch",
            ),
        ]

    async def capture_batch(self, urls: list[str]) -> list[CDPTrafficItem]:
        results: list[CDPTrafficItem] = []
        for url in urls:
            results.extend(await self.capture_traffic(url))
        return results
