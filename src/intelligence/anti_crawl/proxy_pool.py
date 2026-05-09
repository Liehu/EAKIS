"""IP Proxy Pool Manager — Redis 存储 + 内存降级 + 健康检查.

设计要点:
  - 优先使用 Redis 持久化代理池，不可用时降级为内存池
  - 定时健康检查（TCP connect 探测），自动剔除失效代理
  - 按权重轮询：健康代理权重高，近期失败代理权重低
  - 支持动态扩缩容，达到 pool_size 上限后淘汰最低分代理
"""

from __future__ import annotations

import asyncio
import logging
import random
import socket
import time
from dataclasses import dataclass, field

logger = logging.getLogger("eakis.intelligence.proxy_pool")


@dataclass
class ProxyEntry:
    address: str  # host:port
    protocol: str = "http"  # http / https / socks5
    score: float = 1.0  # 0.0 ~ 1.0, 越高越优先
    fail_count: int = 0
    last_check: float = 0.0
    last_used: float = 0.0
    avg_latency: float = 0.0  # 秒

    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.address}"

    @property
    def is_healthy(self) -> bool:
        return self.fail_count < 3 and self.score > 0.2


class InMemoryProxyStore:
    """内存代理存储，作为 Redis 不可用时的降级方案。"""

    def __init__(self) -> None:
        self._proxies: dict[str, ProxyEntry] = {}

    async def add(self, entry: ProxyEntry) -> None:
        self._proxies[entry.address] = entry

    async def remove(self, address: str) -> None:
        self._proxies.pop(address, None)

    async def get_all(self) -> list[ProxyEntry]:
        return list(self._proxies.values())

    async def update(self, address: str, **kwargs: float | int | str) -> None:
        entry = self._proxies.get(address)
        if entry:
            for k, v in kwargs.items():
                setattr(entry, k, v)

    async def count(self) -> int:
        return len(self._proxies)

    async def clear(self) -> None:
        self._proxies.clear()


class RedisProxyStore:
    """Redis 代理存储（需要 redis 异步客户端）。"""

    def __init__(self, redis_url: str = "redis://localhost:6379", key: str = "eakis:proxy_pool") -> None:
        self._redis_url = redis_url
        self._key = key
        self._redis: object | None = None

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
            except Exception:
                logger.warning("Redis 连接失败，将使用内存存储")
                return None
        return self._redis

    async def add(self, entry: ProxyEntry) -> None:
        r = await self._get_redis()
        if r is None:
            return
        import json
        data = {
            "address": entry.address,
            "protocol": entry.protocol,
            "score": entry.score,
            "fail_count": entry.fail_count,
            "last_check": entry.last_check,
            "avg_latency": entry.avg_latency,
        }
        await r.hset(self._key, entry.address, json.dumps(data))

    async def remove(self, address: str) -> None:
        r = await self._get_redis()
        if r:
            await r.hdel(self._key, address)

    async def get_all(self) -> list[ProxyEntry]:
        r = await self._get_redis()
        if r is None:
            return []
        import json
        raw = await r.hgetall(self._key)
        entries: list[ProxyEntry] = []
        for data_str in raw.values():
            try:
                d = json.loads(data_str)
                entries.append(ProxyEntry(
                    address=d["address"],
                    protocol=d.get("protocol", "http"),
                    score=d.get("score", 1.0),
                    fail_count=d.get("fail_count", 0),
                    last_check=d.get("last_check", 0.0),
                    avg_latency=d.get("avg_latency", 0.0),
                ))
            except (json.JSONDecodeError, KeyError):
                continue
        return entries

    async def update(self, address: str, **kwargs: float | int | str) -> None:
        entries = await self.get_all()
        target = next((e for e in entries if e.address == address), None)
        if target:
            for k, v in kwargs.items():
                setattr(target, k, v)
            await self.add(target)

    async def count(self) -> int:
        r = await self._get_redis()
        if r is None:
            return 0
        return await r.hlen(self._key)

    async def clear(self) -> None:
        r = await self._get_redis()
        if r:
            await r.delete(self._key)


class ProxyPool:
    """IP 代理池管理器。

    用法:
        pool = ProxyPool(pool_size=50, redis_url="redis://localhost:6379")
        await pool.initialize(seed_proxies=["1.2.3.4:8080", "5.6.7.8:3128"])
        proxy = await pool.acquire()
        await pool.report(proxy.address, success=True, latency=0.5)
    """

    def __init__(
        self,
        pool_size: int = 50,
        redis_url: str | None = None,
        health_check_interval: int = 300,
        check_timeout: float = 5.0,
    ) -> None:
        self.pool_size = pool_size
        self.health_check_interval = health_check_interval
        self.check_timeout = check_timeout

        if redis_url:
            self._store = RedisProxyStore(redis_url)
            self._fallback = InMemoryProxyStore()
        else:
            self._store = InMemoryProxyStore()
            self._fallback = None

        self._health_task: asyncio.Task | None = None

    async def initialize(self, seed_proxies: list[str] | None = None) -> int:
        for proxy_str in (seed_proxies or []):
            entry = self._parse_proxy(proxy_str)
            if entry:
                await self._store.add(entry)

        count = await self._store.count()
        if count == 0 and self._fallback is not None:
            logger.info("Redis 代理池为空，使用内存降级")
            for proxy_str in (seed_proxies or []):
                entry = self._parse_proxy(proxy_str)
                if entry:
                    await self._fallback.add(entry)
            count = await self._fallback.count()

        logger.info("代理池初始化完成，%d 个代理", count)
        return count

    async def acquire(self) -> ProxyEntry | None:
        """获取一个可用代理（加权随机）。"""
        entries = await self._get_healthy_entries()
        if not entries:
            return None

        weights = [max(e.score, 0.1) for e in entries]
        return random.choices(entries, weights=weights, k=1)[0]

    async def report(self, address: str, success: bool, latency: float = 0.0) -> None:
        """报告代理使用结果，用于动态调整权重。"""
        store = self._get_active_store()
        entry_list = await store.get_all()
        entry = next((e for e in entry_list if e.address == address), None)
        if not entry:
            return

        if success:
            entry.fail_count = max(0, entry.fail_count - 1)
            entry.score = min(1.0, entry.score + 0.05)
            if latency > 0:
                entry.avg_latency = (entry.avg_latency + latency) / 2
        else:
            entry.fail_count += 1
            entry.score = max(0.0, entry.score - 0.15)

        entry.last_used = time.time()
        await store.update(
            address,
            score=entry.score,
            fail_count=entry.fail_count,
            avg_latency=entry.avg_latency,
            last_used=entry.last_used,
        )

        if not entry.is_healthy:
            await store.remove(address)
            logger.info("剔除失效代理: %s (失败 %d 次, 评分 %.2f)", address, entry.fail_count, entry.score)

    async def add_proxies(self, proxies: list[str]) -> int:
        """批量添加代理，超出 pool_size 时淘汰最低分。"""
        store = self._get_active_store()
        added = 0
        for proxy_str in proxies:
            entry = self._parse_proxy(proxy_str)
            if not entry:
                continue
            await store.add(entry)
            added += 1

        current = await store.count()
        if current > self.pool_size:
            entries = await store.get_all()
            entries.sort(key=lambda e: e.score)
            for e in entries[: current - self.pool_size]:
                await store.remove(e.address)

        return added

    async def health_check(self) -> dict[str, int]:
        """主动健康检查：TCP connect 探测所有代理。"""
        store = self._get_active_store()
        entries = await store.get_all()
        stats = {"healthy": 0, "unhealthy": 0, "removed": 0}

        for entry in entries:
            healthy = await self._tcp_check(entry.address)
            entry.last_check = time.time()

            if healthy:
                entry.fail_count = max(0, entry.fail_count - 1)
                entry.score = min(1.0, entry.score + 0.02)
                stats["healthy"] += 1
            else:
                entry.fail_count += 1
                entry.score = max(0.0, entry.score - 0.1)
                stats["unhealthy"] += 1

                if not entry.is_healthy:
                    await store.remove(entry.address)
                    stats["removed"] += 1

            await store.update(
                entry.address,
                score=entry.score,
                fail_count=entry.fail_count,
                last_check=entry.last_check,
            )

        logger.info("健康检查完成: %s", stats)
        return stats

    async def start_health_check_loop(self) -> None:
        """启动后台定时健康检查。"""
        if self._health_task and not self._health_task.done():
            return
        self._health_task = asyncio.create_task(self._health_loop())

    async def stop_health_check_loop(self) -> None:
        if self._health_task and not self._health_task.done():
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

    async def get_stats(self) -> dict[str, int | float]:
        store = self._get_active_store()
        entries = await store.get_all()
        healthy = [e for e in entries if e.is_healthy]
        return {
            "total": len(entries),
            "healthy": len(healthy),
            "avg_score": sum(e.score for e in entries) / len(entries) if entries else 0.0,
            "avg_latency": sum(e.avg_latency for e in healthy) / len(healthy) if healthy else 0.0,
        }

    # --- internal ---

    async def _get_healthy_entries(self) -> list[ProxyEntry]:
        entries = await self._store.get_all()
        healthy = [e for e in entries if e.is_healthy]
        if not healthy and self._fallback:
            entries = await self._fallback.get_all()
            healthy = [e for e in entries if e.is_healthy]
        return healthy

    def _get_active_store(self):
        return self._store

    async def _health_loop(self) -> None:
        while True:
            await asyncio.sleep(self.health_check_interval)
            try:
                await self.health_check()
            except Exception:
                logger.exception("健康检查异常")

    async def _tcp_check(self, address: str) -> bool:
        host, _, port_str = address.rpartition(":")
        try:
            port = int(port_str)
        except ValueError:
            return False

        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self.check_timeout,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError, asyncio.TimeoutError):
            return False

    @staticmethod
    def _parse_proxy(proxy_str: str) -> ProxyEntry | None:
        proxy_str = proxy_str.strip()
        if "://" in proxy_str:
            protocol, rest = proxy_str.split("://", 1)
            address = rest
        else:
            protocol = "http"
            address = proxy_str

        if ":" not in address:
            return None

        return ProxyEntry(address=address, protocol=protocol)
