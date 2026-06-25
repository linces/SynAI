"""
SynAI Driver — Ollama (Local Soberano)
Executa qualquer modelo instalado localmente via Ollama.
Zero custo, zero dependência de rede, zero censura.
Env: OLLAMA_BASE_URL (default: http://localhost:11434)
"""
import os
import httpx
from typing import Optional


class OllamaDriver:
    """Driver local para Ollama — o fallback soberano do SynAI."""

    provider_name = "ollama"
    DEFAULT_MODEL = "llama3"
    DEFAULT_EMBED_MODEL = "nomic-embed-text"

    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.default_model = default_model or self.DEFAULT_MODEL

    def is_available(self) -> bool:
        """Ollama é sempre considerado 'disponível' se base_url estiver configurado.
        A conectividade real só é verificada na primeira chamada."""
        return bool(self.base_url)

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Gera resposta via Ollama local (API /api/generate)."""
        target_model = model or self.default_model
        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")

    async def get_embedding(self, text: str, model: Optional[str] = None) -> Optional[list[float]]:
        """Gera embedding via Ollama (requer modelo de embedding instalado)."""
        embed_model = model or self.DEFAULT_EMBED_MODEL
        payload = {"model": embed_model, "prompt": text}
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(f"{self.base_url}/api/embeddings", json=payload)
                resp.raise_for_status()
                return resp.json().get("embedding")
            except Exception as e:
                print(f"⚠️ [Ollama] Falha ao gerar embedding: {e}")
                return None

    async def list_models(self) -> list[str]:
        """Lista os modelos instalados localmente no Ollama."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                return [m["name"] for m in resp.json().get("models", [])]
            except Exception:
                return []
