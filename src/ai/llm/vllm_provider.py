from __future__ import annotations

from openai import AsyncOpenAI

from .base import LLMProvider


class VLLMProvider(LLMProvider):
    def __init__(self, base_url: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key="EMPTY", base_url=base_url)
        self._model = model

    async def generate(self, messages: list[dict[str, str]], system: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system}, *messages],
        )
        return response.choices[0].message.content or ""
