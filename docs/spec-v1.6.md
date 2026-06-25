# SynAI v1.6 — Especificação Técnica

**Data:** Junho/2026 | **Runtime:** 1.6 | **DSL:** 1.3

---

## 1. Introdução

SynAI é uma DSL declarativa para orquestração de agentes de IA heterogêneos. A partir da v1.5, o runtime tornou-se um **roteador inteligente de modelos** com:

- Registry centralizado de 8 providers
- Fallback automático em cadeia quando um provider falha ou não tem key
- **Model Profiles** (v1.6): `best-coder`, `best-reasoner`, `auto`, etc.
- `MODEL_REGISTRY`: mapeia nomes amigáveis para slugs reais por provider

**Princípios:**
- **Soberania** — nunca dependa de um único provider
- **Declaratividade** — descreva *o quê*, não *como*
- **Progressividade** — zero keys (mock) → adicione providers conforme necessidade
- **Custo Zero Possível** — Groq free + Gemini free + Ollama local = runtime completo gratuito

---

## 2. Arquitetura

```
DSL (.synai) → parse_synai() → AST → build_synai() → AST validado
                                                            │
                                              SynRuntime.execute_workflow()
                                                            │
                                          ┌─────────────────┴─────────────────┐
                                        INTENT                              CONNECT
                                          │                                    │
                                  _dispatch_to_adapter()              data_flow propagation
                                    │             │
                                LLM adapter   TOOL adapter
                                    │
                                call_model(model)
                                    │
                              is_profile(model)?
                              ┌─────┴──────┐
                             YES           NO
                              │             │
                        _call_profile()  FALLBACK_CHAIN
                        (MODEL_PROFILES)  (por provider)
```

### Camadas

| Camada | Arquivo | Responsabilidade |
|---|---|---|
| DSL | `parse.py` | `parse_synai()` — DSL → AST (Lark) |
| Validação | `weave.py` | `build_synai()` — JSONSchema + dependências |
| Grafo | `weaver.py` | `weave_linker()` — NetworkX |
| Profiles | `profiles.py` | `MODEL_REGISTRY` + `MODEL_PROFILES` |
| Runtime | `runtime.py` | `SynRuntime` — execução, fallback, embeddings |
| Providers | `providers/` | Drivers individuais (DeepSeek, Groq, etc.) |
| Protocol | `interfaces.py` | `LLMProvider` Protocol |

---

## 3. Sintaxe DSL (v1.3)

```synai
orchestrator "Pipeline" {

  agents {
    analyst: LLM {
      model: "deepseek-reasoner"       # modelo específico
      capabilities: ["reason", "analyze"]
    }
    coder: LLM {
      model: "best-coder"              # perfil semântico (v1.6)
    }
    fetcher: TOOL {
      function: "web_search"
    }
  }

  workflow "Main" {
    intent "Buscar" {
      agent: fetcher
      input: "notícias de IA"
    }
    connect fetcher.output -> analyst.input { async: true timeout: 30s }
    intent "Analisar" {
      agent: analyst
      input: result("Buscar")
    }
    connect analyst.output -> coder.input { retry: 2 }
    intent "Codificar" {
      agent: coder
      input: result("Analisar")
    }
  }
}

run "Pipeline" with workflow "Main"
```

### Opções de Connect

| Opção | Tipo | Descrição |
|---|---|---|
| `async` | bool | Não bloqueia o próximo intent |
| `timeout` | duração | Timeout da operação |
| `retry` | int | Tentativas em falha |
| `filter` | string | Filtro de condição (planejado v2.0) |
| `transform` | string | Transformação de dados (planejado v2.0) |

---

## 4. Model Profiles (v1.6)

### Perfis Disponíveis

| Profile | Prioridade (resumida) | Uso Ideal |
|---|---|---|
| `best-coder` | deepseek-coder → qwen-coder → codestral → gpt-4o | Código, debug, refactoring |
| `best-reasoner` | deepseek-reasoner → qwen-reasoner → claude-sonnet → gpt-4o | Análise, planejamento |
| `best-fast` | llama-70b (Groq) → gemini-flash → deepseek-chat | Alta frequência, baixa latência |
| `best-free` | llama-70b → gemini-flash → qwen-72b → llama3-local | Zero custo |
| `best-rag` | gemini-flash-2.5 (1M ctx) → gemini-pro → claude-sonnet | Contexto longo |
| `best-writer` | claude-sonnet → gpt-4o → qwen-72b | Prosa, documentação |
| `best-local` | llama3-local → codellama-local → mistral-local | Offline, soberano |
| `auto` | tenta tudo em ordem de capacidade | SynAI decide |

### Fluxo Interno de _call_profile()

1. Obtém lista de `MODEL_PROFILES[profile]`
2. Para cada nome amigável: `resolve_model(name)` → `(provider_alias, api_slug)` via `MODEL_REGISTRY`
3. Se não está no registry, trata como slug direto e infere provider via `_infer_provider()`
4. Verifica `driver.is_available()` — pula sem API key
5. Tenta `driver.generate(prompt, model=api_slug)`
6. Em falha, avança para o próximo

---

## 5. Providers e Drivers

### FALLBACK_CHAIN

```python
["anthropic", "openai", "grok", "deepseek", "openrouter", "google", "groq", "ollama"]
```

### Drivers

| Alias | Driver | Protocol/SDK | Env Var | Modelos-chave |
|---|---|---|---|---|
| `anthropic` | `AnthropicDriver` | `httpx` | `ANTHROPIC_API_KEY` | claude-sonnet, claude-haiku |
| `openai` | `OpenAIDriver` | `httpx` | `OPENAI_API_KEY` | gpt-4o, gpt-4o-mini |
| `deepseek` | `DeepSeekDriver` | `httpx` | `DEEPSEEK_API_KEY` | deepseek-chat, deepseek-coder, deepseek-reasoner (R1) |
| `openrouter` | `OpenRouterDriver` | `httpx` | `OPENROUTER_API_KEY` | qwen-72b, codestral, llama-70b |
| `groq` | `GroqDriver` | `httpx` | `GROQ_API_KEY` | llama-3.3-70b-versatile |
| `ollama` | `OllamaDriver` | `httpx` | `OLLAMA_BASE_URL` | qualquer modelo local |
| `grok` | `GrokDriver` | `httpx` | `XAI_API_KEY` | grok-3 |
| `google` | `GoogleDriver` | `httpx` | `GOOGLE_API_KEY` | gemini-pro, gemini-flash |

### LLMProvider Protocol

```python
class LLMProvider(Protocol):
    provider_name: str
    def is_available(self) -> bool: ...
    async def generate(self, prompt: str, model: str, **kwargs) -> str: ...
    async def get_embedding(self, text: str) -> Optional[list[float]]: ...
```

---

## 6. SynRuntime — API Pública

```python
rt = SynRuntime(real=True)

# Registro
rt.register_llm_provider("deepseek", DeepSeekDriver(), set_default=True)
rt.register_tool("web_search", my_search_func)
rt.register_toolkit({"f1": func1, "f2": func2})

# Telemetria
rt.add_event_listener(my_callback)

# Chamada de modelo (com fallback automático)
result = await rt.call_model(
    model="best-coder",        # perfil, nome amigável ou slug direto
    prompt="...",
    max_tokens=1024,
    preferred_provider="groq", # força tentativa deste primeiro (opcional)
)

# Workflow completo
result = await rt.execute_workflow(validated_ast, run_decl)

# Embeddings (RAG)
vector = await rt.get_embedding("texto")
```

---

## 7. Variáveis de Ambiente

```bash
ANTHROPIC_API_KEY=      # Claude
OPENAI_API_KEY=         # GPT-4o
DEEPSEEK_API_KEY=       # DeepSeek V3/R1
XAI_API_KEY=            # Grok 3
OPENROUTER_API_KEY=     # 300+ modelos
GROQ_API_KEY=           # Llama ultra-rápido
OLLAMA_BASE_URL=http://localhost:11434
GOOGLE_API_KEY=         # Gemini
```

---

## 8. Telemetria de Roteamento (v1.6)

O `SynRuntime` fornece um gancho de telemetria assíncrona por meio de `add_event_listener(callback)`. O callback recebe `(event_name: str, payload: dict)` com os seguintes eventos:

1. **`routing_start`**: Iniciando chamada a um modelo ou perfil.
2. **`routing_skip`**: Pulando um provider candidato (ex: sem chave de API).
3. **`routing_try`**: Tentando requisição HTTPX para um driver.
4. **`routing_fail`**: Driver falhou com exceção ou erro HTTP.
5. **`routing_success`**: Chamada bem-sucedida (contém snippet da resposta).
6. **`routing_failed_all`**: Todos os candidatos falharam.

---

## 9. Limitações v1.6

- `if`/`repeat` (controle de fluxo) planejados para v2.0
- `transform` e `filter` nos connects são declarativos, mas ainda sem executor real
- Ollama: sem servidor rodando → cai para o próximo provider silenciosamente

---

_SynAI v1.6 — Roteador inteligente de modelos de IA._
