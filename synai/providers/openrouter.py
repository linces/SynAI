"""
SynAI Driver — OpenRouter
Gateway para +300 modelos: Qwen, Mistral, Llama, Codestral, WizardCoder, etc.
Um único API key dá acesso a praticamente todo o ecossistema open-source.

FreeTier: modelos com sufixo ':free' não consomem crédito (rate-limitados).
    Ative prefer_free=True para usar automaticamente o free tier quando disponível.

Env: OPENROUTER_API_KEY
"""
import os
import httpx
from typing import Optional


class OpenRouterDriver:
    """Driver para OpenRouter — gateway para +300 modelos com um único API key."""

    provider_name = "openrouter"
    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "qwen/qwen-2.5-72b-instruct"
    DEFAULT_FREE_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

    # Modelos recomendados (slugs válidos no OpenRouter)
    RECOMMENDED = {
        "geral":         "qwen/qwen-2.5-72b-instruct",
        "code":          "qwen/qwen-2.5-coder-32b-instruct",
        "code_fast":     "mistralai/codestral-latest",
        "reasoning":     "qwen/qwq-32b",
        "llama_big":     "meta-llama/llama-3.3-70b-instruct",
        "mistral":       "mistralai/mistral-7b-instruct",
    }

    # Catálogo de modelos gratuitos do OpenRouter (:free = sem custo)
    FREE_MODELS: list = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "qwen/qwen3-coder:free",
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "openai/gpt-oss-120b:free",
        "openai/gpt-oss-20b:free",
        "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        "cohere/north-mini-code:free",
        "liquid/lfm-2.5-1.2b-thinking:free",
        "liquid/lfm-2.5-1.2b-instruct:free",
        "openrouter/free",
    ]

    # Melhor modelo free por categoria
    FREE_BEST: dict = {
        "geral":     "meta-llama/llama-3.3-70b-instruct:free",
        "code":      "qwen/qwen3-coder:free",
        "reasoning": "openrouter/free",
        "fast":      "meta-llama/llama-3.2-3b-instruct:free",
        "balanced":  "google/gemma-4-31b-it:free",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        site_url: str = "https://synai.dev",
        site_name: str = "SynAI",
        prefer_free: bool = False,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.site_url = site_url    # Exigido pela política da OpenRouter
        self.site_name = site_name  # Exibido no dashboard da OpenRouter
        self.prefer_free = prefer_free  # Se True, prefere modelos :free quando disponível

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
        # Se prefer_free e o modelo não tem :free, tenta versao free primeiro
        resolved_model = model
        if self.prefer_free and ":free" not in model:
            free_candidate = model + ":free"
            if free_candidate in self.FREE_MODELS:
                resolved_model = free_candidate
                print(f"   [OpenRouter] prefer_free: usando '{resolved_model}' em vez de '{model}'")

        payload = {
            "model": resolved_model,
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
            if resp.status_code >= 400:
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("error", {}).get("message", resp.text)
                except Exception:
                    error_msg = resp.text
                raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {error_msg}")
            
            data = resp.json()

            # Tratar erros retornados no corpo (OpenRouter usa HTTP 200 com erro no JSON)
            if "error" in data:
                raise RuntimeError(f"OpenRouter error: {data['error']}")

            return data["choices"][0]["message"]["content"] or ""

    async def get_embedding(self, text: str) -> Optional[list[float]]:
        """OpenRouter não expõe API de embeddings diretamente."""
        return None

    def list_free_models(self) -> list:
        """Retorna todos os modelos gratuitos catalogados."""
        return list(self.FREE_MODELS)

    def get_best_free_model(self, category: str = "geral") -> str:
        """Retorna o melhor modelo gratuito para uma categoria."""
        return self.FREE_BEST.get(category, self.DEFAULT_FREE_MODEL)

    def enable_free_mode(self) -> None:
        """Ativa o modo prefer_free para esta instância."""
        self.prefer_free = True
        print("[OpenRouter] Modo prefer_free ativado — priorizando modelos :free")
