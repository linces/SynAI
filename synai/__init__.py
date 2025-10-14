__version__ = "1.4"

import os
from dotenv import load_dotenv

from .parse import parse_synai
from .weave import build_synai
from .weaver import weave_linker
from .cli import cli
from .runtime import SynRuntime

# Carrega variáveis de ambiente automaticamente (.env)
load_dotenv()

__all__ = [
    "parse_synai",
    "build_synai",
    "weave_linker",
    "cli",
    "SynRuntime",
]
