"""
synai.providers — Registry de Drivers de LLM para o SynAI.

Cada driver implementa o protocolo LLMProvider (synai.interfaces).
Imports são lazy por padrão para não quebrar instalações parciais.

Providers disponíveis:
    anthropic   → AnthropicDriver  (Claude)
    openai      → OpenAIDriver     (GPT-4o)
    google      → GoogleDriver     (Gemini)
    deepseek    → DeepSeekDriver   (DeepSeek Chat / Coder / Reasoner)
    openrouter  → OpenRouterDriver (Qwen, Mistral, Llama, 300+ modelos)
    groq        → GroqDriver       (Llama ultra-rápido)
    ollama      → OllamaDriver     (Local soberano)
    grok        → GrokDriver       (xAI Grok)
"""

from .deepseek import DeepSeekDriver
from .openrouter import OpenRouterDriver
from .groq import GroqDriver
from .ollama import OllamaDriver
from .grok import GrokDriver

__all__ = [
    "DeepSeekDriver",
    "OpenRouterDriver",
    "GroqDriver",
    "OllamaDriver",
    "GrokDriver",
]
