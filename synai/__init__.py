__version__ = "1.5"

import os
from dotenv import load_dotenv

from .parse import parse_synai
from .weave import build_synai
from .weaver import weave_linker
from .cli import cli
from .runtime import SynRuntime, FALLBACK_CHAIN
from .interfaces import LLMProvider

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
    # Providers
    "DeepSeekDriver",
    "OpenRouterDriver",
    "GroqDriver",
    "OllamaDriver",
    "GrokDriver",
]
