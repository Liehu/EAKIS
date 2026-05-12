import json
from typing import Any

from src.intelligence.services.base import BaseLLMClient


class StubLLMClient(BaseLLMClient):
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        if "DSL" in prompt or "fofa" in prompt.lower() or "搜索语法" in prompt:
            # 从 prompt 中提取关键词和域名
            import re

            # 提取域名
            domain_match = re.search(r"域名[：:]\s*([^\n]+)", prompt)
            domains = domain_match.group(1).split(", ") if domain_match else ["example.com"]
            primary_domain = domains[0].strip()

            # 提取关键词
            keyword_match = re.search(r"关键词[：:]\s*([^\n]+)", prompt)
            keywords = keyword_match.group(1).split(", ") if keyword_match else ["目标"]
            primary_kw = keywords[0].strip()

            # 提取平台列表
            platforms = ["fofa", "hunter", "shodan"]
            for platform in ["fofa", "hunter", "shodan", "quake", "bing"]:
                if platform in prompt.lower():
                    if platform not in platforms:
                        platforms.append(platform)

            # 动态生成 DSL
            result = {}
            if "fofa" in prompt.lower():
                result["fofa"] = f'domain="{primary_domain}" && title="{primary_kw}"'
            if "hunter" in prompt.lower():
                result["hunter"] = f'domain.suffix="{primary_domain}" && web.title="{primary_kw}"'
            if "shodan" in prompt.lower():
                result["shodan"] = f'org:"{primary_kw}" http.title:"{primary_kw}"'
            if "quake" in prompt.lower():
                result["quake"] = f'app:"{primary_kw}"'

            return json.dumps(result, ensure_ascii=False)

        if "数据源" in prompt or "source" in prompt.lower():
            return json.dumps({
                "recommended_sources": ["news", "official", "legal", "asset_engine"],
                "reasoning": "基于目标企业规模和行业特征推荐全类别数据源",
            })
        return f"LLM模拟响应：已处理请求"
