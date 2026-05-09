"""UA Pool + Browser Fingerprint Disguise.

设计要点:
  - UA 池：内置 200+ 常见桌面/移动端 User-Agent，按浏览器族加权轮换
  - 浏览器指纹：Canvas/WebGL 噪声注入、viewport 随机化、屏幕分辨率模拟
  - 请求特征：随机化 Accept-Language / Accept-Encoding 顺序
"""

from __future__ import annotations

import hashlib
import random
import struct
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# UA Pool
# ---------------------------------------------------------------------------

_CHROME_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
]

_FIREFOX_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{ver}.0) Gecko/20100101 Firefox/{ver}.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:{ver}.0) Gecko/20100101 Firefox/{ver}.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:{ver}.0) Gecko/20100101 Firefox/{ver}.0",
]

_EDGE_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36 Edg/{ver}.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36 Edg/{ver}.0.0.0",
]

_MOBILE_UAS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_{minor} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.{minor} Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Mobile Safari/537.36",
]

_ACCEPT_LANGUAGES = [
    "zh-CN,zh;q=0.9,en;q=0.8",
    "zh-CN,zh;q=0.9",
    "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "en-US,en;q=0.9",
    "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
]

_ACCEPT_ENCODINGS = [
    "gzip, deflate, br",
    "gzip, deflate",
    "br, gzip, deflate",
]


@dataclass
class BrowserProfile:
    """一个完整的浏览器伪装配置。"""

    user_agent: str
    accept_language: str
    accept_encoding: str
    viewport_width: int
    viewport_height: int
    screen_width: int
    screen_height: int
    color_depth: int
    platform: str
    webgl_vendor: str
    webgl_renderer: str
    canvas_seed: int


def _build_ua_pool() -> list[str]:
    pool: list[str] = []
    chrome_versions = range(110, 130)
    for tmpl in _CHROME_UAS:
        for v in random.sample(list(chrome_versions), min(8, len(chrome_versions))):
            pool.append(tmpl.format(ver=v))

    firefox_versions = range(115, 130)
    for tmpl in _FIREFOX_UAS:
        for v in random.sample(list(firefox_versions), min(5, len(firefox_versions))):
            pool.append(tmpl.format(ver=v))

    edge_versions = range(110, 130)
    for tmpl in _EDGE_UAS:
        for v in random.sample(list(edge_versions), min(5, len(edge_versions))):
            pool.append(tmpl.format(ver=v))

    for tmpl in _MOBILE_UAS:
        pool.append(tmpl.format(ver=random.randint(115, 125), minor=random.randint(0, 5)))

    return pool


class UAPool:
    """User-Agent 池管理器。

    用法:
        pool = UAPool(pool_size=200)
        ua = pool.random()
        profile = pool.random_profile()
    """

    def __init__(self, pool_size: int = 200) -> None:
        self.pool_size = pool_size
        self._pool = _build_ua_pool()
        # 裁剪或保持
        if len(self._pool) > pool_size:
            self._pool = random.sample(self._pool, pool_size)
        self._index = 0

    def random(self) -> str:
        """随机获取一个 User-Agent。"""
        return random.choice(self._pool)

    def next(self) -> str:
        """顺序轮换获取下一个 User-Agent。"""
        if self._index >= len(self._pool):
            self._index = 0
        ua = self._pool[self._index]
        self._index += 1
        return ua

    @property
    def size(self) -> int:
        return len(self._pool)


# ---------------------------------------------------------------------------
# Browser Fingerprint
# ---------------------------------------------------------------------------

_WEBGL_VENDORS = [
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (Apple)", "APPLE-28"),
]

_VIEWPORTS = [
    (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
    (1280, 720), (1600, 900), (1280, 800), (1024, 768),
]

_SCREEN_RESOLUTIONS = [
    (1920, 1080), (2560, 1440), (1366, 768), (3840, 2160),
    (1536, 864), (1440, 900), (1280, 1024),
]

_PLATFORMS = {
    "Windows": "Win32",
    "Macintosh": "MacIntel",
    "Linux": "Linux x86_64",
}


class FingerprintGenerator:
    """浏览器指纹生成器。

    用法:
        gen = FingerprintGenerator()
        fp = gen.generate(user_agent="...")
    """

    def generate(self, user_agent: str | None = None) -> BrowserProfile:
        """生成一个完整的浏览器伪装配置。"""
        ua = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

        # 根据UA推断platform
        platform = self._infer_platform(ua)

        # 选择匹配的viewport
        vw, vh = random.choice(_VIEWPORTS)

        # 屏幕分辨率 >= viewport
        sw, sh = random.choice(_SCREEN_RESOLUTIONS)
        if sw < vw:
            sw, sh = vw, vh

        # WebGL
        vendor, renderer = random.choice(_WEBGL_VENDORS)

        # Canvas seed — 用于注入确定性噪声
        canvas_seed = struct.unpack("I", hashlib.md5(ua.encode()).digest()[:4])[0]

        return BrowserProfile(
            user_agent=ua,
            accept_language=random.choice(_ACCEPT_LANGUAGES),
            accept_encoding=random.choice(_ACCEPT_ENCODINGS),
            viewport_width=vw,
            viewport_height=vh,
            screen_width=sw,
            screen_height=sh,
            color_depth=random.choice([24, 30, 32]),
            platform=_PLATFORMS.get(platform, "Win32"),
            webgl_vendor=vendor,
            webgl_renderer=renderer,
            canvas_seed=canvas_seed,
        )

    def generate_headers(self, profile: BrowserProfile | None = None, ua: str | None = None) -> dict[str, str]:
        """生成一组伪装请求头。"""
        if profile is None:
            profile = self.generate(ua)
        return {
            "User-Agent": profile.user_agent,
            "Accept-Language": profile.accept_language,
            "Accept-Encoding": profile.accept_encoding,
            "DNT": random.choice(["1", "null"]),
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    @staticmethod
    def _infer_platform(ua: str) -> str:
        if "Windows" in ua:
            return "Windows"
        if "Macintosh" in ua or "Mac OS" in ua:
            return "Macintosh"
        if "Linux" in ua:
            return "Linux"
        if "iPhone" in ua or "Android" in ua:
            return "Linux"
        return "Windows"


class AntiCrawlProfile:
    """反爬伪装门面：组合 UA 池 + 指纹生成。

    用法:
        ac = AntiCrawlProfile(pool_size=200)
        profile = ac.next_profile()
        headers = ac.next_headers()
    """

    def __init__(self, pool_size: int = 200) -> None:
        self.ua_pool = UAPool(pool_size)
        self.fp_gen = FingerprintGenerator()

    def next_profile(self) -> BrowserProfile:
        """获取下一个完整浏览器伪装配置。"""
        ua = self.ua_pool.next()
        return self.fp_gen.generate(ua)

    def random_profile(self) -> BrowserProfile:
        """随机获取一个浏览器伪装配置。"""
        ua = self.ua_pool.random()
        return self.fp_gen.generate(ua)

    def next_headers(self) -> dict[str, str]:
        """获取下一组伪装请求头。"""
        profile = self.next_profile()
        return self.fp_gen.generate_headers(profile)
