"""
SynAI Driver — OpenRouter
Gateway para +300 modelos: Qwen, Mistral, Llama, Codestral, WizardCoder, etc.
Um único API key dá acesso a praticamente todo o ecossistema open-source.
Env: OPENROUTER_API_KEY
"""
import os
import httpx
from typing import Optional


class OpenRouterDriver:
    """Driver para OpenRouter — gateway para +300 modelos com um único API key."""

    provider_name = "openrouter"
    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "qwen/qwen2.5-72b-instruct"

    # Modelos recomendados (slugs válidos no OpenRouter)
    RECOMMENDED = {
        "geral":         "qwen/qwen2.5-72b-instruct",
        "code":          "qwen/qwen2.5-coder-32b-instruct",
        "code_fast":     "mistralai/codestral-latest",
        "reasoning":     "qwen/qwq-32b",
        "llama_big":     "meta-llama/llama-3.3-70b-instruct",
        "mistral":       "mistralai/mistral-7b-instruct",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        site_url: str = "https://synai.dev",
        site_name: str = "SynAI",
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.site_url = site_url    # Exigido pela política da OpenRouter
        self.site_name = site_name  # Exibido no dashboard da OpenRouter

    def is_available(self) -> bool:
        """Retorna True se a API key está configurada."""
        return bool(self.api_key)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,   # Obrigatório pela API
            "X-Title": self.site_name,        # Opcional mas recomendado
            "Content-Type": "application/json",
        }

    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Gera resposta via OpenRouter (qualquer modelo disponível no gateway)."""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

            # Tratar erros retornados no corpo (OpenRouter usa HTTP 200 com erro no JSON)
            if "error" in data:
                raise RuntimeError(f"OpenRouter error: {data['error']}")

            return data["choices"][0]["message"]["content"] or ""

    async def get_embedding(self, text: str) -> Optional[list[float]]:
        """OpenRouter não expõe API de embeddings diretamente."""
        return None
