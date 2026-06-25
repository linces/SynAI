__version__ = "1.6"

import os
from dotenv import load_dotenv

from .parse import parse_synai
from .weave import build_synai
from .weaver import weave_linker
from .cli import cli
from .runtime import SynRuntime, FALLBACK_CHAIN
from .interfaces import LLMProvider
from .profiles import MODEL_PROFILES, MODEL_REGISTRY, is_profile, resolve_model

# Providers — imports diretos para conveniência
from .providers import (
    DeepSeekDriver,
    OpenRouterDriver,
    GroqDriver,
    OllamaDriver,
    GrokDriver,
)

# Carrega variáveis de ambiente automaticamente (.env)
load_dotenv()

__all__ = [
    # Core
    "parse_synai",
    "build_synai",
    "weave_linker",
    "cli",
    "SynRuntime",
    "FALLBACK_CHAIN",
    "LLMProvider",
    # Model Routing
    "MODEL_PROFILES",
    "MODEL_REGISTRY",
    "is_profile",
    "resolve_model",
    # Providers
    "DeepSeekDriver",
    "OpenRouterDriver",
    "GroqDriver",
    "OllamaDriver",
    "GrokDriver",
]
