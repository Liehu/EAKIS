from __future__ import annotations

from src.api_crawler.agents.version_tracker import VersionTracker
from src.api_crawler.models import (
    ClassifiedInterface,
    CrawlMethod,
    InterfaceType,
    ParameterInfo,
)


def _iface(
    path: str,
    method: str = "GET",
    params: list[ParameterInfo] | None = None,
    **kw,
) -> ClassifiedInterface:
    return ClassifiedInterface(
        path=path,
        method=method,
        api_type=InterfaceType.QUERY,
        parameters=params or [],
        crawl_method=CrawlMethod.STATIC,
        **kw,
    )


class TestChecksum:
    def test_same_interface_same_checksum(self):
        tracker = VersionTracker()
        a = _iface("/api/v1/users", "GET")
        b = _iface("/api/v1/users", "GET")
        assert tracker.compute_checksum(a) == tracker.compute_checksum(b)

    def test_different_path_different_checksum(self):
        tracker = VersionTracker()
        a = _iface("/api/v1/users", "GET")
        b = _iface("/api/v1/orders", "GET")
        assert tracker.compute_checksum(a) != tracker.compute_checksum(b)

    def test_different_method_different_checksum(self):
        tracker = VersionTracker()
        a = _iface("/api/v1/users", "GET")
        b = _iface("/api/v1/users", "POST")
        assert tracker.compute_checksum(a) != tracker.compute_checksum(b)

    def test_different_params_different_checksum(self):
        tracker = VersionTracker()
        a = _iface(
            "/api/v1/users",
            "GET",
            params=[ParameterInfo(name="page", location="query")],
        )
        b = _iface(
            "/api/v1/users",
            "GET",
            params=[ParameterInfo(name="id", location="path")],
        )
        assert tracker.compute_checksum(a) != tracker.compute_checksum(b)


class TestVersionTracking:
    def test_new_interface_gets_version_1(self):
        tracker = VersionTracker()
        iface = _iface("/api/v1/users", "GET")
        result = tracker.track(iface, existing_checksums={})
        assert result.version == 1

    def test_unchanged_interface_keeps_version(self):
        tracker = VersionTracker()
        iface = _iface("/api/v1/users", "GET")
        cs = tracker.compute_checksum(iface)
        result = tracker.track(iface, existing_checksums={cs: 3})
        assert result.version == 3

    def test_changed_interface_gets_new_version(self):
        tracker = VersionTracker()
        new = _iface("/api/v1/users", "POST")
        result = tracker.track(new, existing_checksums={})
        assert result.version == 1

    def test_batch_tracking(self):
        tracker = VersionTracker()
        ifaces = [
            _iface("/api/v1/a", "GET"),
            _iface("/api/v1/b", "GET"),
        ]
        results = tracker.track_batch(ifaces, existing_checksums={})
        assert all(r.version == 1 for r in results)
