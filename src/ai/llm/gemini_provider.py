from __future__ import annotations

from google import genai
from google.genai import types as gtypes

from .base import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def generate(self, messages: list[dict[str, str]], system: str) -> str:
        contents = [
            gtypes.Content(
                role="model" if m["role"] == "assistant" else "user",
                parts=[gtypes.Part.from_text(text=m["content"])],
            )
            for m in messages
        ]
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=contents,
            config=gtypes.GenerateContentConfig(system_instruction=system),
        )
        return response.text or ""
