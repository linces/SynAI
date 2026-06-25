"""
SynAI Driver — Google Gemini
Acesso direto à API do Gemini (v1beta) usando httpx para evitar dependências extras.
Env: GOOGLE_API_KEY
"""
import os
import httpx
from typing import Optional


class GoogleDriver:
    """Driver para Google Gemini API — httpx-based."""

    provider_name = "google"
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY", "")

    def is_available(self) -> bool:
        """Retorna True se a API key do Google está configurada."""
        return bool(self.api_key)

    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Gera resposta usando a API do Gemini."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature
            }
        }
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text or ""
            except (KeyError, IndexError) as e:
                raise RuntimeError(f"Unexpected response format from Gemini: {data}. Error: {e}")

    async def get_embedding(self, text: str) -> Optional[list[float]]:
        """Gera embeddings usando o modelo de embedding padrão do Google."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.api_key}"
        
        payload = {
            "content": {
                "parts": [{"text": text}]
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            try:
                return data["embedding"]["values"]
            except KeyError:
                return None
