from typing import Any


class LLMClient:
    def __init__(self, model: str = "gpt-4o", api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        # TODO: call LLM provider
        raise NotImplementedError
