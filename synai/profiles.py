"""
SynAI — Model Registry & Profiles

MODEL_REGISTRY: mapeia nomes amigáveis para (provider_alias, api_slug).
    Permite usar "deepseek-coder" no DSL em vez de "deepseek-coder-v2-instruct".

MODEL_PROFILES: agrupa modelos por capacidade/objetivo.
    Usado quando o agente DSL define model: "best-coder" ou model: "auto".
    O SynAI tenta cada modelo na lista em ordem até obter resposta.

Uso no DSL SynAI:
    agent analyst {
        model: "best-reasoner"
    }

    agent coder {
        model: "auto"
    }

    agent analyst {
        model: "deepseek-reasoner"   # modelo específico — também funciona
    }
"""

from typing import Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# MODEL REGISTRY — nome amigável → (provider_alias, api_slug_real)
# ─────────────────────────────────────────────────────────────────────────────
MODEL_REGISTRY: dict[str, Tuple[str, str]] = {

    # ── DeepSeek ─────────────────────────────────────────────────────────────
    "deepseek-chat":       ("deepseek",   "deepseek-chat"),
    "deepseek-coder":      ("deepseek",   "deepseek-coder"),
    "deepseek-reasoner":   ("deepseek",   "deepseek-reasoner"),   # R1

    # ── OpenRouter: Qwen ─────────────────────────────────────────────────────
    "qwen-72b":            ("openrouter", "qwen/qwen2.5-72b-instruct"),
    "qwen-coder":          ("openrouter", "qwen/qwen2.5-coder-32b-instruct"),
    "qwen-reasoner":       ("openrouter", "qwen/qwq-32b"),         # QwQ

    # ── OpenRouter: Mistral ──────────────────────────────────────────────────
    "codestral":           ("openrouter", "mistralai/codestral-latest"),
    "mistral-7b":          ("openrouter", "mistralai/mistral-7b-instruct"),
    "mistral-nemo":        ("openrouter", "mistralai/mistral-nemo"),

    # ── OpenRouter: Llama via OpenRouter (contexto longo) ────────────────────
    "llama-70b-or":        ("openrouter", "meta-llama/llama-3.3-70b-instruct"),

    # ── Groq: Llama & Mixtral (ultra-rápido) ─────────────────────────────────
    "llama-70b":           ("groq",       "llama-3.3-70b-versatile"),
    "llama-8b":            ("groq",       "llama-3.1-8b-instant"),
    "mixtral":             ("groq",       "mixtral-8x7b-32768"),
    "gemma2":              ("groq",       "gemma2-9b-it"),

    # ── Anthropic ────────────────────────────────────────────────────────────
    "claude-sonnet":       ("anthropic",  "claude-sonnet-4-5"),
    "claude-haiku":        ("anthropic",  "claude-haiku-3-5"),
    "claude-opus":         ("anthropic",  "claude-opus-4-5"),

    # ── OpenAI ───────────────────────────────────────────────────────────────
    "gpt-4o":              ("openai",     "gpt-4o"),
    "gpt-4o-mini":         ("openai",     "gpt-4o-mini"),
    "gpt-5":               ("openai",     "gpt-5"),                # quando disponível
    "gpt-5-mini":          ("openai",     "gpt-5-mini"),

    # ── Google ───────────────────────────────────────────────────────────────
    "gemini-flash":        ("google",     "gemini-2.0-flash"),
    "gemini-pro":          ("google",     "gemini-2.5-pro"),
    "gemini-flash-2.5":    ("google",     "gemini-2.5-flash"),

    # ── xAI Grok ─────────────────────────────────────────────────────────────
    "grok-3":              ("grok",       "grok-3"),
    "grok-mini":           ("grok",       "grok-3-mini"),
    "grok-2":              ("grok",       "grok-2"),

    # ── Ollama (local) ────────────────────────────────────────────────────────
    "llama3-local":        ("ollama",     "llama3"),
    "codellama-local":     ("ollama",     "codellama"),
    "mistral-local":       ("ollama",     "mistral"),
    "phi3-local":          ("ollama",     "phi3"),
}


# ─────────────────────────────────────────────────────────────────────────────
# MODEL PROFILES — perfis semânticos com fallback em cascata
# ─────────────────────────────────────────────────────────────────────────────
MODEL_PROFILES: dict[str, list[str]] = {

    # Melhor para código: compilação, debug, geração de funções, refactoring
    "best-coder": [
        "deepseek-coder",       # DeepSeek Coder V2 — SOTA em code benchmarks
        "qwen-coder",           # Qwen2.5 Coder 32B — open-source excelente
        "codestral",            # Mistral especializado em código
        "gpt-4o",               # Forte, mas mais caro
        "claude-sonnet",        # Bom em código, ótimo em explicações
        "gemini-pro",           # Gemini 2.5 Pro — excelente raciocínio e código
        "gemini-flash",         # Gemini 2.0 Flash — fallback rápido
        "grok-3",               # Grok 3 — ótimo codificador
        "llama-70b",            # Rápido, bom em tarefas simples de código
    ],

    # Melhor para raciocínio: análise, planejamento, chain-of-thought, agentes
    "best-reasoner": [
        "deepseek-reasoner",    # R1 — raciocínio passo-a-passo (o1-like)
        "qwen-reasoner",        # QwQ-32B — forte em lógica e math
        "claude-sonnet",        # Melhor raciocínio da Anthropic
        "gpt-4o",               # Sólido e confiável
        "gemini-pro",           # Contexto longo, bom em análise
        "gemini-flash",         # Gemini 2.0 Flash — fallback rápido
        "grok-3",               # Alternativa xAI
    ],

    # Melhor em velocidade: respostas rápidas, pipelines de alta frequência
    "best-fast": [
        "llama-70b",            # Groq ~800 tok/s — o mais rápido disponível
        "llama-8b",             # Ainda mais rápido, menor qualidade
        "gemini-flash-2.5",     # Google Flash — rápido e barato
        "deepseek-chat",        # V3 — equilibrio velocidade/qualidade
        "gpt-4o-mini",          # Rápido e barato
        "mistral-7b",           # Leve, livre
    ],

    # Melhor custo-benefício: gratuitos ou ultra-baratos como prioridade
    "best-free": [
        "llama-70b",            # Groq free tier
        "gemini-flash-2.5",     # Google free tier (1M ctx)
        "qwen-72b",             # OpenRouter free tier
        "deepseek-chat",        # ~$0.14/1M tokens
        "mistral-7b",           # OpenRouter free
        "gemma2",               # Groq free
        "llama3-local",         # Ollama — completamente grátis
    ],

    # Melhor para RAG: contexto longo, sumarização, recuperação semântica
    "best-rag": [
        "gemini-flash-2.5",     # 1M tokens de contexto nativo
        "gemini-pro",           # Ainda mais capaz com contexto longo
        "deepseek-chat",        # 128K ctx, eficiente
        "qwen-72b",             # 128K ctx
        "claude-sonnet",        # 200K ctx
        "gpt-4o",               # 128K ctx
    ],

    # Melhor para escrita: copywriting, documentação, emails, conteúdo
    "best-writer": [
        "claude-sonnet",        # Melhor escrita criativa/técnica do mercado
        "gpt-4o",               # Excelente em prosa
        "qwen-72b",             # Boa alternativa open-source
        "deepseek-chat",        # Boa qualidade de escrita
        "gemini-pro",           # Bom para conteúdo longo
    ],

    # Local/soberano: prioriza modelos que rodam na máquina do usuário
    "best-local": [
        "llama3-local",         # Ollama — meta llama3
        "codellama-local",      # Ollama — especializado em código
        "mistral-local",        # Ollama — mistral 7B
        "phi3-local",           # Ollama — Microsoft phi3
        "llama-70b",            # Groq — melhor externo como fallback
        "deepseek-chat",        # DeepSeek — fallback externo
    ],

    # Auto: deixa o SynAI decidir, tenta tudo do mais capaz ao mais leve
    "auto": [
        "deepseek-chat",
        "qwen-72b",
        "claude-sonnet",
        "gpt-4o",
        "gemini-flash-2.5",
        "llama-70b",
        "deepseek-coder",
        "mistral-7b",
        "gemma2",
        "llama3-local",
    ],
}


def is_profile(name: str) -> bool:
    """Retorna True se o nome é um perfil de modelo (ex: 'best-coder', 'auto')."""
    return name in MODEL_PROFILES


def resolve_model(name: str) -> Optional[Tuple[str, str]]:
    """
    Resolve um nome amigável para (provider_alias, api_slug).

    Returns:
        Tuple (provider, slug) se o nome está no registry.
        None se o nome deve ser tratado como slug direto.
    """
    return MODEL_REGISTRY.get(name)


def get_profile_models(profile: str) -> list[str]:
    """
    Retorna a lista de nomes de modelo de um perfil.
    Retorna lista com o próprio nome se não for um perfil.
    """
    return MODEL_PROFILES.get(profile, [profile])
