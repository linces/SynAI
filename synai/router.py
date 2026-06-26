"""
SynAI — Model Router Engine
============================

Centraliza toda a lógica de roteamento multi-provider baseada em política.

OpenRouter é o hub principal. Políticas controlam qual caminho os LLMs percorrem.

Políticas disponíveis:
    free          — Zero custo. Ollama → OpenRouter Free → Groq → Mock
    cheapest      — Alias de free
    local         — Soberania total. Só Ollama (sem rede externa)
    balanced      — Custo-benefício. Ollama → OpenRouter → Groq → DeepSeek → Flash → GPT → Claude
    premium       — Máxima qualidade. Claude → GPT → Gemini → DeepSeek → OpenRouter → Groq → Ollama
    openrouter_first — OpenRouter como hub absoluto, resto como fallback

Uso:
    from synai.router import RouterEngine

    chain = RouterEngine.get_chain("free")
    # → ["ollama", "openrouter", "groq"]

    runtime = SynRuntime(policy="free")
    runtime = SynRuntime(policy="premium")

No DSL .synx:
    runtime {
        policy: free
    }
"""

from typing import List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# OPENROUTER FREE TIER — modelos com acesso gratuito via OpenRouter
# Sufixo :free = sem custo, rate-limitado mas funcional.
# ─────────────────────────────────────────────────────────────────────────────
OPENROUTER_FREE_MODELS: List[str] = [
    "meta-llama/llama-3.3-70b-instruct:free",     # Llama 3.3 70B — excelente geral
    "meta-llama/llama-3.1-8b-instruct:free",      # Llama 3.1 8B — rápido
    "qwen/qwen2.5-72b-instruct:free",             # Qwen 2.5 72B — forte
    "qwen/qwen2.5-coder-32b-instruct:free",       # Qwen Coder 32B — código
    "qwen/qwq-32b:free",                          # QwQ — raciocínio
    "mistralai/mistral-7b-instruct:free",         # Mistral 7B — leve e rápido
    "google/gemma-3-27b-it:free",                 # Gemma 3 27B — Google open
    "google/gemma-3-12b-it:free",                 # Gemma 3 12B — compacto
    "deepseek/deepseek-r1:free",                  # DeepSeek R1 — raciocínio
    "deepseek/deepseek-chat-v3-0324:free",        # DeepSeek V3 — geral
    "microsoft/phi-4:free",                       # Phi-4 — eficiente
    "nvidia/llama-3.1-nemotron-70b-instruct:free",# Nemotron 70B — NVIDIA
    "nousresearch/deephermes-3-llama-3-8b:free",  # DeepHermes 3 — instrução
]

# Melhor modelo free por categoria
OPENROUTER_FREE_BEST: dict = {
    "geral":      "meta-llama/llama-3.3-70b-instruct:free",
    "code":       "qwen/qwen2.5-coder-32b-instruct:free",
    "reasoning":  "deepseek/deepseek-r1:free",
    "fast":       "mistralai/mistral-7b-instruct:free",
    "balanced":   "qwen/qwen2.5-72b-instruct:free",
}


# ─────────────────────────────────────────────────────────────────────────────
# POLICY CHAINS — ordem de tentativa de providers por política
#
# Regras:
#   - "free": nunca inclui anthropic, openai, google, grok, deepseek pagos
#   - "premium": começa pelas APIs de maior qualidade, OpenRouter é fallback
#   - "balanced": OpenRouter como hub principal (80%), premium como exceção
#   - "local": nenhuma chamada de rede externa
#   - "openrouter_first": OpenRouter antes de tudo, igual ao hub ideal
# ─────────────────────────────────────────────────────────────────────────────
POLICY_CHAINS: dict[str, List[str]] = {

    # ── FREE ─────────────────────────────────────────────────────────────────
    # Zero custo garantido. Nunca toca em APIs pagas.
    # Ollama primeiro (local), OpenRouter free tier, Groq free tier.
    "free": [
        "ollama",       # local — gratuito, soberano
        "openrouter",   # hub free tier: Llama/Qwen/Gemma/DeepSeek grátis
        "groq",         # Llama via Groq — free tier ultra-rápido
    ],

    # ── LOCAL ─────────────────────────────────────────────────────────────────
    # Somente modelos locais Ollama. Zero dependência de rede.
    "local": [
        "ollama",
    ],

    # ── BALANCED ──────────────────────────────────────────────────────────────
    # OpenRouter como hub central (80% das chamadas vão aqui).
    # Ollama como aquecedor local, premium como última opção.
    "balanced": [
        "ollama",       # 1. Local — zero custo
        "openrouter",   # 2. Hub: Qwen/Llama/Mistral/DeepSeek/Gemma (free + paid)
        "groq",         # 3. Groq — ultra-rápido, free tier generoso
        "deepseek",     # 4. DeepSeek — custo extraordinário (~$0.14/1M)
        "google",       # 5. Gemini Flash — rápido, barato, 1M ctx
        "openai",       # 6. GPT — robusto, amplamente testado
        "anthropic",    # 7. Claude — premium, melhor raciocínio geral
        "grok",         # 8. Grok — alternativa xAI
    ],

    # ── PREMIUM ───────────────────────────────────────────────────────────────
    # Máxima qualidade. APIs de ponta primeiro, OpenRouter como fallback.
    "premium": [
        "anthropic",    # 1. Claude — melhor raciocínio e escrita
        "openai",       # 2. GPT-4o / GPT-5 — robusto
        "google",       # 3. Gemini Pro — contexto longo, multimodal
        "grok",         # 4. Grok 3 — forte em código
        "deepseek",     # 5. DeepSeek — custo-benefício extraordinário
        "openrouter",   # 6. Hub: Qwen/Llama/Mistral como fallback
        "groq",         # 7. Groq — fallback rápido
        "ollama",       # 8. Local — último recurso
    ],

    # ── OPENROUTER FIRST ──────────────────────────────────────────────────────
    # OpenRouter como hub absoluto. Ollama como suporte local.
    # APIs premium só em último caso.
    "openrouter_first": [
        "openrouter",   # 1. Hub central — +300 modelos
        "ollama",       # 2. Local — fallback soberano
        "groq",         # 3. Groq — rápido e free
        "deepseek",     # 4. DeepSeek — barato e capaz
        "google",       # 5. Gemini — fallback Google
        "openai",       # 6. GPT — fallback premium
        "anthropic",    # 7. Claude — fallback premium
        "grok",         # 8. Grok — último premium
    ],
}

# Aliases
POLICY_CHAINS["cheapest"] = POLICY_CHAINS["free"]
POLICY_CHAINS["sovereign"] = POLICY_CHAINS["local"]

# Conjunto de providers que nunca devem ser usados na política "free"
FREE_BLOCKED_PROVIDERS: set = {"anthropic", "openai", "grok", "google", "deepseek"}

# Políticas que jamais usam providers pagos
ZERO_COST_POLICIES: set = {"free", "cheapest", "local", "sovereign"}

# Lista de todas as policies válidas
VALID_POLICIES: List[str] = list(POLICY_CHAINS.keys())


# ─────────────────────────────────────────────────────────────────────────────
# RouterEngine
# ─────────────────────────────────────────────────────────────────────────────
class RouterEngine:
    """
    Motor de roteamento central do SynAI.

    Responsável por:
    - Retornar a cadeia de providers para uma política
    - Verificar se um provider é permitido em uma política
    - Fornecer o melhor modelo free tier para uma categoria
    """

    @staticmethod
    def get_chain(policy: str) -> List[str]:
        """
        Retorna a lista ordenada de providers para a política informada.

        Args:
            policy: Nome da política ("free", "balanced", "premium", etc.)

        Returns:
            Lista de aliases de providers em ordem de tentativa.

        Raises:
            ValueError: Se a política não for reconhecida.
        """
        policy = policy.strip().lower()
        if policy not in POLICY_CHAINS:
            valid = ", ".join(sorted(POLICY_CHAINS.keys()))
            raise ValueError(
                f"[RouterEngine] Política '{policy}' desconhecida. "
                f"Válidas: {valid}"
            )
        return POLICY_CHAINS[policy]

    @staticmethod
    def is_provider_allowed(provider: str, policy: str) -> bool:
        """
        Verifica se um provider e permitido sob a politica informada.

        - local/sovereign: apenas 'ollama' permitido (zero rede externa)
        - free/cheapest:   bloqueia apenas providers pagos (openrouter e groq sao permitidos)
        - demais:          todos os providers permitidos
        """
        policy = policy.strip().lower()

        # local/sovereign: apenas ollama
        if policy in {"local", "sovereign"}:
            return provider == "ollama"

        # free/cheapest: bloqueia providers com custo por token
        if policy in {"free", "cheapest"} and provider in FREE_BLOCKED_PROVIDERS:
            return False

        return True

    @staticmethod
    def get_free_model(category: str = "geral") -> str:
        """
        Retorna o slug do melhor modelo OpenRouter gratuito para uma categoria.

        Args:
            category: "geral", "code", "reasoning", "fast", "balanced"

        Returns:
            Slug do modelo no formato OpenRouter (com :free)
        """
        return OPENROUTER_FREE_BEST.get(category, OPENROUTER_FREE_BEST["geral"])

    @staticmethod
    def list_free_models() -> List[str]:
        """Retorna todos os modelos gratuitos catalogados no OpenRouter."""
        return list(OPENROUTER_FREE_MODELS)

    @staticmethod
    def describe_policy(policy: str) -> str:
        """Retorna uma descrição legível da política."""
        descriptions = {
            "free":            "Zero custo -- Ollama -> OpenRouter Free -> Groq",
            "cheapest":        "Zero custo (alias de free)",
            "local":           "Soberano -- apenas Ollama, sem rede externa",
            "sovereign":       "Soberano (alias de local)",
            "balanced":        "Custo-beneficio -- OpenRouter como hub, premium como excecao",
            "premium":         "Maxima qualidade -- Claude -> GPT -> Gemini -> fallbacks",
            "openrouter_first":"Hub OpenRouter -- OpenRouter -> Ollama -> resto",
        }
        return descriptions.get(policy.lower(), f"Politica '{policy}' sem descricao.")

    @staticmethod
    def validate_policy(policy: str) -> Optional[str]:
        """
        Valida e normaliza o nome de uma política.

        Returns:
            Nome normalizado se válido, None caso contrário.
        """
        normalized = policy.strip().lower()
        return normalized if normalized in POLICY_CHAINS else None
