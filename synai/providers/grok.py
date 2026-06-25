"""
SynAI Driver — xAI Grok
API compatível com OpenAI SDK via base_url alternativo (https://api.x.ai/v1).
Driver dedicado para manter o registry explícito e não poluir o driver OpenAI.
Env: XAI_API_KEY
"""
import os
from typing import Optional
from openai import AsyncOpenAI


class GrokDriver:
    """Driver para xAI Grok (API compatível com OpenAI)."""

    provider_name = "grok"
    BASE_URL = "https://api.x.ai/v1"
    DEFAULT_MODEL = "grok-3"

    MODELS = [
        "grok-3",         # Mais poderoso
        "grok-3-mini",    # Mais rápido/barato
        "grok-2",         # Geração anterior
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("XAI_API_KEY", "")
        self._client: Optional[AsyncOpenAI] = None

    def is_available(self) -> bool:
        """Retorna True se a API key está configurada."""
        return bool(self.api_key)

    def _get_client(self) -> AsyncOpenAI:
        if not self._client:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.BASE_URL,
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Gera resposta via xAI Grok."""
        client = self._get_client()
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        return resp.choices[0].message.content or ""

    async def get_embedding(self, text: str) -> Optional[list[float]]:
        """xAI não possui API pública de embeddings."""
        return None
