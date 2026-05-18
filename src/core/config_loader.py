"""统一的配置加载器"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .config_paths import ENGINES_YAML, CRAWLER_YAML


@dataclass
class EngineConfig:
    """引擎配置"""
    name: str
    display_name: str
    description: str
    base: Dict[str, Any]
    api: Optional[Dict[str, Any]] = None
    cdp: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None


@dataclass
class GlobalConfig:
    """全局配置"""
    default_mode: str = "api"
    cdp: Dict[str, Any] = None
    api: Dict[str, Any] = None
    anti_crawl: Dict[str, Any] = None


class ConfigLoader:
    """统一的配置加载器"""

    def __init__(self):
        self._config_cache = {}
        self._engines_cache = {}

    def load_engines(self) -> Dict[str, EngineConfig]:
        """加载所有引擎配置"""
        if "engines" in self._config_cache:
            return self._config_cache["engines"]

        if not ENGINES_YAML.exists():
            raise FileNotFoundError(f"Engines config file not found: {ENGINES_YAML}")

        with open(ENGINES_YAML, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        engines = {}

        # 加载普通搜索引擎
        for name, cfg in config.get("web_engines", {}).items():
            engines[name] = EngineConfig(
                name=name,
                display_name=cfg["display_name"],
                description=cfg.get("description", ""),
                base=cfg["base"],
                api=cfg.get("api", {}),
                cdp=cfg.get("cdp", {}),
                settings=cfg.get("settings", {})
            )

        # 加载专业情报搜索引擎
        for name, cfg in config.get("intelligence_engines", {}).items():
            engines[name] = EngineConfig(
                name=name,
                display_name=cfg["display_name"],
                description=cfg.get("description", ""),
                base=cfg["base"],
                api=cfg.get("api", {}),
                cdp=cfg.get("cdp", {}),
                settings=cfg.get("settings", {})
            )

        self._config_cache["engines"] = engines
        return engines

    def load_global_config(self) -> GlobalConfig:
        """加载全局配置"""
        if "global" in self._config_cache:
            return self._config_cache["global"]

        if not ENGINES_YAML.exists():
            return GlobalConfig()

        with open(ENGINES_YAML, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        global_cfg = config.get("global", {})

        self._config_cache["global"] = GlobalConfig(
            default_mode=global_cfg.get("default_mode", "api"),
            cdp=global_cfg.get("cdp", {}),
            api=global_cfg.get("api", {}),
            anti_crawl=global_cfg.get("anti_crawl", {})
        )

        return self._config_cache["global"]

    def get_engine_config(self, engine_name: str) -> Optional[EngineConfig]:
        """获取特定引擎的配置"""
        engines = self.load_engines()
        return engines.get(engine_name)

    def is_cdp_enabled(self, engine_name: str) -> bool:
        """检查引擎是否启用了 CDP 模式"""
        config = self.get_engine_config(engine_name)
        if config and config.cdp:
            return config.cdp.get("enabled", False)
        return False

    def is_api_enabled(self, engine_name: str) -> bool:
        """检查引擎是否启用了 API 模式"""
        config = self.get_engine_config(engine_name)
        if config and config.api:
            return config.api.get("enabled", False)
        return False

    def get_cdp_selectors(self, engine_name: str) -> Dict[str, str]:
        """获取 CDP 选择器配置"""
        config = self.get_engine_config(engine_name)
        if config and config.cdp:
            return {
                "result_selector": config.cdp.get("result_selector", ""),
                "title_selector": config.cdp.get("title_selector", ""),
                "link_selector": config.cdp.get("link_selector", ""),
                "snippet_selector": config.cdp.get("snippet_selector", ""),
                "load_timeout": config.cdp.get("load_timeout", 30),
                "wait_for_selector": config.cdp.get("wait_for_selector", "")
            }
        return {}

    def get_api_config(self, engine_name: str) -> Dict[str, Any]:
        """获取 API 配置"""
        config = self.get_engine_config(engine_name)
        if config and config.api:
            return config.api
        return {}


# 全局配置加载器实例
config_loader = ConfigLoader()