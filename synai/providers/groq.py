"""
SynAI Driver — Groq Cloud
Inferência ultra-rápida (~800 tok/s). Ideal para agentes com latência crítica.
Suporta: Llama 3.3, Mixtral, Gemma2, entre outros.
Env: GROQ_API_KEY
"""
import os
from typing import Optional


class GroqDriver:
    """Driver para Groq Cloud — inferência open-source ultra-rápida."""

    provider_name = "groq"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    # Modelos disponíveis via Groq (gratuitos no free tier)
    MODELS = [
        "llama-3.3-70b-versatile",   # Llama 3.3 70B — melhor custo-benefício
        "llama-3.1-8b-instant",       # Ultra-rápido, menor qualidade
        "mixtral-8x7b-32768",         # Mixtral MoE — bom para tarefas longas
        "gemma2-9b-it",               # Google Gemma2 — leve e capaz
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self._client = None

    def is_available(self) -> bool:
        """Retorna True se a API key está configurada."""
        return bool(self.api_key)

    def _get_client(self):
        """Lazy import do SDK Groq para não quebrar se não instalado."""
        if not self._client:
            try:
                from groq import AsyncGroq
                self._client = AsyncGroq(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "SDK groq não instalado. Execute: pip install groq>=0.9.0"
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
        """Gera resposta via Groq Cloud."""
        client = self._get_client()
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""

    async def get_embedding(self, text: str) -> Optional[list[float]]:
        """Groq não possui API de embeddings."""
        return None
