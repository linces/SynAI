# SynAI — The Sovereign Intelligence Language

> *Orquestre qualquer IA de forma declarativa. Agnóstico de provider. Soberano por design.*

SynAI é uma **DSL (Domain Specific Language)** para orquestração de agentes de IA heterogêneos.
Ela separa o **QUÊ** (intenção declarada) do **COMO** (provider, modelo, API) — e decide automaticamente
qual LLM usar, em qual ordem, com fallback em cadeia.

---

## Por que SynAI?

| Problema | Solução SynAI |
|---|---|
| Dependência de um único provider (OpenAI lock-in) | Registry de 8 providers + fallback automático |
| Troca de modelo = reescrita de código | `model: "best-coder"` — o runtime decide |
| Falha de API quebra o workflow inteiro | Fallback em cadeia: Claude → GPT → DeepSeek → Groq → Ollama → Mock |
| Boilerplate para cada nova API | Driver em ~50 linhas, registrado em 1 linha |
| Custo alto em 100% dos requests | `best-free` profile prioriza modelos gratuitos automaticamente |

---

## Início Rápido

```bash
pip install synai
```

```python
from synai import SynRuntime

rt = SynRuntime(real=True)  # Auto-carrega e registra todos os 8 drivers padrão

# O runtime tenta DeepSeek → OpenRouter → Gemini → etc. automaticamente
resposta = await rt.call_model("best-reasoner", "Analise este código...")
```

```bash
cp .env.example .env   # preencha as keys dos providers que você tem
```

---

## A DSL SynAI

### Definição de Agentes

```synai
orchestrator "MyPipeline" {

  agents {

    # Agente com modelo específico
    analyst: LLM {
      model: "deepseek-reasoner"
      capabilities: ["reason", "analyze"]
    }

    # Agente com perfil semântico — SynAI escolhe o melhor disponível
    coder: LLM {
      model: "best-coder"
      capabilities: ["code", "generate"]
    }

    # Sempre o mais rápido disponível
    summarizer: LLM {
      model: "best-fast"
      capabilities: ["summarize"]
    }

    # SynAI decide tudo — tenta na ordem da fallback chain
    auto_agent: LLM {
      model: "auto"
    }

  }

  workflow "Analyze_and_Code" {
    intent "Analisar Requisitos" {
      agent: analyst
      input: "Descreva os requisitos do sistema de pagamentos."
    }

    connect analyst.output -> coder.input { async: true }

    intent "Gerar Implementação" {
      agent: coder
      input: result("Analisar Requisitos")
    }

    connect coder.output -> summarizer.input { timeout: 30s }

    intent "Resumir Resultado" {
      agent: summarizer
    }
  }

}

run "MyPipeline" with workflow "Analyze_and_Code"
```

---

## Model Profiles (v1.6)

Em vez de especificar um modelo diretamente, use um **perfil semântico**:

| Profile | Prioridade | Uso ideal |
|---|---|---|
| `best-coder` | deepseek-coder → qwen-coder → codestral → gpt-4o | Geração de código, debug, refactoring |
| `best-reasoner` | deepseek-reasoner → qwen-reasoner → claude-sonnet → gpt-4o | Análise, planejamento, chain-of-thought |
| `best-fast` | llama-70b (Groq) → gemini-flash → deepseek-chat | Alta frequência, baixa latência |
| `best-free` | llama-70b → gemini-flash → qwen-72b → deepseek-chat | Zero custo, máxima soberania |
| `best-rag` | gemini-flash-2.5 (1M ctx) → gemini-pro → claude-sonnet | Contexto longo, recuperação semântica |
| `best-writer` | claude-sonnet → gpt-4o → qwen-72b | Copywriting, documentação, prosa |
| `best-local` | llama3-local → codellama-local → mistral-local | Soberania total, offline, sem custo |
| `auto` | Tenta tudo em ordem de capacidade | Deixa o SynAI decidir |

---

## Providers Suportados (v1.6)

| Provider | Driver | Env Var | Modelos |
|---|---|---|---|
| Anthropic | built-in | `ANTHROPIC_API_KEY` | Claude Sonnet, Haiku, Opus |
| OpenAI | built-in | `OPENAI_API_KEY` | GPT-4o, GPT-4o-mini |
| **DeepSeek** | `DeepSeekDriver` | `DEEPSEEK_API_KEY` | deepseek-chat, deepseek-coder, deepseek-reasoner (R1) |
| **OpenRouter** | `OpenRouterDriver` | `OPENROUTER_API_KEY` | 300+ modelos: Qwen, Mistral, Llama, Codestral... |
| **Groq** | `GroqDriver` | `GROQ_API_KEY` | Llama 3.3 70B, Mixtral, Gemma2 (~800 tok/s) |
| **Ollama** | `OllamaDriver` | `OLLAMA_BASE_URL` | Qualquer modelo local (sem API key) |
| **xAI Grok** | `GrokDriver` | `XAI_API_KEY` | Grok-3, Grok-3-mini |
| Google | built-in | `GOOGLE_API_KEY` | Gemini Flash, Gemini Pro |

---

## Fallback Chain

Quando um provider falha ou não tem API key configurada, o SynAI avança automaticamente:

```
Anthropic (Claude)
       ↓
  OpenAI (GPT)
       ↓
  xAI (Grok)
       ↓
 DeepSeek V3/R1
       ↓
OpenRouter (Qwen / Mistral / Llama)
       ↓
 Google (Gemini)
       ↓
  Groq (Llama)
       ↓
Ollama (local)
       ↓
    Mock
```

---

## Uso Python

```python
import asyncio
from synai import (
    SynRuntime,
    DeepSeekDriver, OpenRouterDriver, GroqDriver, OllamaDriver, GrokDriver,
    MODEL_PROFILES, MODEL_REGISTRY,
)

async def main():
    rt = SynRuntime(real=True)

    # Registre apenas os providers que você tem keys
    rt.register_llm_provider("deepseek",   DeepSeekDriver(),    set_default=True)
    rt.register_llm_provider("openrouter", OpenRouterDriver())
    rt.register_llm_provider("groq",       GroqDriver())
    rt.register_llm_provider("ollama",     OllamaDriver())      # sem key, local

    # Chamar com perfil semântico
    code = await rt.call_model("best-coder", "Escreva um quicksort em Python.")

    # Chamar com modelo específico
    analysis = await rt.call_model("deepseek-reasoner", "Analise este contrato...")

    # Chamar com auto (SynAI decide)
    summary = await rt.call_model("auto", "Resuma em 3 pontos: ...")

    # Executar workflow DSL completo
    from synai import parse_synai, build_synai
    ast = parse_synai(open("pipeline.synai").read())
    validated = build_synai(ast)
    run_decl = next(d for d in validated["declarations"] if d["type"] == "Run")
    result = await rt.execute_workflow(validated, run_decl)
    print(result)

asyncio.run(main())
```

---

## Ferramentas (Tools)

```python
def search_web(query: str) -> str:
    return f"Resultados para: {query}"

async def generate_report(data: str) -> str:
    return f"Relatório: {data}"

rt.register_tool("search_web", search_web)
rt.register_tool("generate_report", generate_report)

# No DSL:
# agent researcher: TOOL { function: "search_web" }
```

---

## Telemetria de Roteamento (Novidade v1.6)

O runtime do SynAI expõe um sistema de hooks de telemetria assíncronos para permitir o monitoramento em tempo real do fluxo de decisões, skips e fallbacks.

### Registrar um Listener de Telemetria

```python
rt = SynRuntime(real=True)

def my_telemetry_listener(event_name: str, payload: dict):
    print(f"[{event_name}] {payload}")

# Adiciona o listener
rt.add_event_listener(my_telemetry_listener)
```

### Eventos Despachados

| Evento | Payload | Descrição |
|---|---|---|
| `routing_start` | `{"model": str, "type": str, "prompt": str}` | Disparado ao iniciar a chamada de um modelo ou perfil. |
| `routing_skip` | `{"model": str, "provider": str, "reason": str}` | Disparado quando um provider é ignorado (ex: sem chave de API). |
| `routing_try` | `{"model": str, "provider": str, "slug": str}` | Disparado antes de realizar a requisição HTTPX para o driver. |
| `routing_fail` | `{"model": str, "provider": str, "error": str}` | Disparado quando o driver falha com erro ou HTTP status não-200. |
| `routing_success` | `{"model": str, "provider": str, "response": str}` | Disparado quando a requisição é concluída com sucesso. |
| `routing_failed_all` | `{"model": str}` | Disparado quando todos os candidatos falham. |

---

## Estrutura do Projeto

```
synai/
├── __init__.py         # Exports: SynRuntime, drivers, MODEL_PROFILES
├── runtime.py          # SynRuntime: execute_workflow, call_model, fallback chain
├── profiles.py         # MODEL_REGISTRY + MODEL_PROFILES (8 perfis semânticos)
├── interfaces.py       # LLMProvider Protocol (provider_name, is_available, generate)
├── parse.py            # Parser DSL → AST (Lark)
├── weave.py            # Validação semântica (JSONSchema)
├── weaver.py           # Linker de grafo (NetworkX)
├── cli.py              # CLI: synai build / run / link
└── providers/
    ├── deepseek.py     # DeepSeek Chat / Coder / Reasoner
    ├── openrouter.py   # Gateway 300+ modelos
    ├── groq.py         # Llama ultra-rápido
    ├── ollama.py       # Local soberano
    └── grok.py         # xAI Grok
```

---

## CLI

```bash
synai build pipeline.synai -o pipeline.synx --verbose   # Parseia e valida
synai link pipeline.synx                                 # Gera grafo de dependências
synai run pipeline.synx --real                           # Executa com APIs reais
synai run pipeline.synx                                  # Executa em modo mock
```

---

## Filosofia

- **Soberania**: Nunca dependa de um único provider. O SynAI garante que seu sistema continua funcionando.
- **Declaratividade**: Descreva *o que* você quer, não *como* obter. O runtime decide.
- **Progressividade**: Comece com `mock=False`, adicione keys progressivamente, e o sistema escala automaticamente.
- **Custo Zero Possível**: Com Groq free tier + Gemini free tier + Ollama local, você tem um runtime completo sem gastar nada.

---

*SynAI v1.6 — O roteador inteligente de modelos de IA.*
