"""
SynAI Driver — OpenAI GPT
Acesso direto à API do OpenAI usando httpx para evitar dependências extras.
Env: OPENAI_API_KEY
"""
import os
import httpx
from typing import Optional


class OpenAIDriver:
    """Driver para OpenAI GPT API — httpx-based."""

    provider_name = "openai"
    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")

    def is_available(self) -> bool:
        """Retorna True se a API key da OpenAI está configurada."""
        return bool(self.api_key)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Gera resposta usando a API do OpenAI."""
        url = "https://api.openai.com/v1/chat/completions"
        
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
                return data["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError) as e:
                raise RuntimeError(f"Unexpected response format from OpenAI: {data}. Error: {e}")

    async def get_embedding(self, text: str) -> Optional[list[float]]:
        """Gera embeddings usando a API do OpenAI."""
        url = "https://api.openai.com/v1/embeddings"
        
        payload = {
            "model": "text-embedding-3-small",
            "input": text
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            try:
                return data["data"][0]["embedding"]
            except (KeyError, IndexError):
                return None
