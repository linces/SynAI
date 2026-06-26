"""
Diagnostico SynAI -> OpenRouter
Testa a chamada real ao OpenRouter com varios modelos free,
tratando 429 com fallback para o proximo modelo da lista.
"""
import asyncio
import sys
import os
import httpx

# encoding seguro para Windows cp1252
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# garante que o pacote synai seja encontrado
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from synai.runtime import SynRuntime
from synai.providers.openrouter import OpenRouterDriver


MODELS_TO_TRY = [
    "meta-llama/llama-3.2-3b-instruct:free",        # menor, menos rate-limited
    "google/gemma-4-26b-a4b-it:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",        # popular - mais sujeito a 429
    "openrouter/free",                               # auto-select do OR
]

PROMPT = "Em uma frase curta: qual e a capital do Brasil?"


async def test_driver_direct(driver: OpenRouterDriver) -> None:
    print("\n[TESTE 1] Chamada direta ao driver OpenRouter com multiplos modelos:")
    for model in MODELS_TO_TRY:
        try:
            print(f"  -> Tentando: {model}...")
            result = await driver.generate(prompt=PROMPT, model=model, max_tokens=64)
            print(f"  OK SUCESSO com '{model}':")
            print(f"     {result.strip()}")
            return  # primeiro sucesso encerra
        except RuntimeError as e:
            msg = str(e)
            if "429" in msg:
                print(f"  [429] Rate-limit em '{model}' — tentando proximo...")
            else:
                print(f"  [ERRO] '{model}': {msg[:120]}")
        except Exception as e:
            print(f"  [ERRO inesperado] '{model}': {type(e).__name__}: {e}")
    print("  FALHA: todos os modelos free retornaram erro.")


async def test_via_runtime(rt: SynRuntime) -> None:
    print("\n[TESTE 2] call_model() com fallback chain (policy=free):")
    # usa o modelo menor para ter mais chance de passar no free tier
    model = "meta-llama/llama-3.2-3b-instruct:free"
    try:
        result = await rt.call_model(
            model=model,
            prompt=PROMPT,
            max_tokens=64,
        )
        print(f"  OK call_model() retornou: {result.strip()[:200]}")
    except Exception as e:
        print(f"  ERRO em call_model(): {type(e).__name__}: {e}")


async def test_api_connectivity(key: str) -> None:
    """Verifica se conseguimos falar com a API do OpenRouter sem autenticacao."""
    print("\n[TESTE 0] Conectividade com api.openrouter.ai...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://openrouter.ai/api/v1/models",
                                 headers={"Authorization": f"Bearer {key}"})
            if r.status_code == 200:
                data = r.json()
                total = len(data.get("data", []))
                print(f"  OK API acessivel — {total} modelos listados no catalogo.")
            else:
                print(f"  ATENCAO: status {r.status_code} — {r.text[:200]}")
    except Exception as e:
        print(f"  ERRO de conectividade: {type(e).__name__}: {e}")


async def main():
    key = os.getenv("OPENROUTER_API_KEY", "")
    print(f"\n[INFO] OPENROUTER_API_KEY: {'SIM (' + key[:12] + '...)' if key else 'NAO ENCONTRADA!'}")
    if not key:
        print("FATAL: sem API key.")
        return

    # Teste 0: ping na API
    await test_api_connectivity(key)

    # Instancia runtime
    print("\n[INFO] Instanciando SynRuntime(real=True, policy='free')...")
    rt = SynRuntime(real=True, policy="free")
    or_driver = rt.llm_providers.get("openrouter")

    print(f"\n[INFO] Driver openrouter: registrado={bool(or_driver)}, "
          f"is_available={or_driver.is_available() if or_driver else 'N/A'}, "
          f"prefer_free={getattr(or_driver, 'prefer_free', 'N/A')}")

    if not or_driver:
        print("FATAL: driver openrouter nao registrado.")
        return

    # Teste 1: direto no driver
    await test_driver_direct(or_driver)

    # Teste 2: via runtime com fallback
    await test_via_runtime(rt)

    print("\n[DIAGNOSTICO COMPLETO]")


if __name__ == "__main__":
    asyncio.run(main())
