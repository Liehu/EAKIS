from __future__ import annotations

import hashlib
import json

from src.api_crawler.models import ClassifiedInterface


class VersionTracker:
    def compute_checksum(self, iface: ClassifiedInterface) -> str:
        payload = json.dumps(
            {
                "path": iface.path,
                "method": iface.method,
                "params": sorted(
                    [
                        {"name": p.name, "location": p.location, "type": p.type}
                        for p in iface.parameters
                    ]
                ),
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def track(
        self,
        iface: ClassifiedInterface,
        existing_checksums: dict[str, int],
    ) -> ClassifiedInterface:
        cs = self.compute_checksum(iface)
        iface.checksum = cs

        if cs in existing_checksums:
            iface.version = existing_checksums[cs]
        else:
            # New or changed interface
            iface.version = 1

        return iface

    def track_batch(
        self,
        ifaces: list[ClassifiedInterface],
        existing_checksums: dict[str, int],
    ) -> list[ClassifiedInterface]:
        return [self.track(i, existing_checksums) for i in ifaces]
