"""
SynAI Driver — Anthropic Claude
Acesso direto à API do Anthropic usando httpx para evitar dependências extras.
Env: ANTHROPIC_API_KEY
"""
import os
import httpx
from typing import Optional


class AnthropicDriver:
    """Driver para Anthropic Claude API — httpx-based."""

    provider_name = "anthropic"
    DEFAULT_MODEL = "claude-haiku-3-5"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    def is_available(self) -> bool:
        """Retorna True se a API key da Anthropic está configurada."""
        return bool(self.api_key)

    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Gera resposta usando a API do Anthropic."""
        url = "https://api.anthropic.com/v1/messages"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            try:
                return data["content"][0]["text"] or ""
            except (KeyError, IndexError) as e:
                raise RuntimeError(f"Unexpected response format from Anthropic: {data}. Error: {e}")

    async def get_embedding(self, text: str) -> Optional[list[float]]:
        """Anthropic não possui API de embeddings."""
        return None
