"""
SynAI Driver — DeepSeek
Suporta: deepseek-chat, deepseek-coder, deepseek-reasoner (R1)
API compatível com OpenAI SDK via base_url alternativo.
Env: DEEPSEEK_API_KEY
"""
import os
from typing import Optional
from openai import AsyncOpenAI


class DeepSeekDriver:
    """Driver para a API da DeepSeek (compatível com OpenAI SDK)."""

    provider_name = "deepseek"
    BASE_URL = "https://api.deepseek.com/v1"
    DEFAULT_MODEL = "deepseek-chat"

    # Modelos disponíveis
    MODELS = [
        "deepseek-chat",       # V3 — uso geral, muito competitivo
        "deepseek-coder",      # Especializado em código
        "deepseek-reasoner",   # R1 — raciocínio passo-a-passo (o1-like)
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
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
        """Gera resposta via DeepSeek API."""
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
        """DeepSeek não possui API pública de embeddings (use Google ou Ollama)."""
        return None
