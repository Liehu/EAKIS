import json
from typing import Any

from src.intelligence.services.base import BaseLLMClient


class StubLLMClient(BaseLLMClient):
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        if "DSL" in prompt or "fofa" in prompt.lower() or "搜索语法" in prompt:
            return json.dumps({
                "fofa": 'domain="example.com" && title="目标"',
                "hunter": 'domain.suffix="example.com" && web.title="目标"',
                "shodan": 'org:"Example Corp" http.title:"目标"',
            })
        if "数据源" in prompt or "source" in prompt.lower():
            return json.dumps({
                "recommended_sources": ["news", "official", "legal", "asset_engine"],
                "reasoning": "基于目标企业规模和行业特征推荐全类别数据源",
            })
        return f"LLM模拟响应：已处理请求"
