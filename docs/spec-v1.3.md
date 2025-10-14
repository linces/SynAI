# SynAI v1.3 -- Documento Técnico Completo (14/10/2025)

## 1. Introdução

### 1.1 Visão Geral

SynAI é uma linguagem de programação declarativa projetada especificamente para orquestração de agentes de IA heterogêneos. Ela abstrai protocolos de comunicação subjacentes (ex: MCP da Anthropic, HTTP, gRPC, xAI API) para permitir fluxos colaborativos simples e escaláveis. Versão 1.3 introduz runtime real com adapters multi-provider (Claude/Grok/OpenAI), suporte a options avançadas (transform/retry/filter/step) e handling de erros/billing com fallback mock.

**Princípios Fundamentais:**

- **Declaratividade**: Descreva _o que_ as IAs devem alcançar, não _como_ implementá-lo.
- **Interoperabilidade**: Suporte a múltiplos transportes/APIs sem boilerplate.
- **Modularidade**: Agentes plugáveis com capabilities declaradas.
- **Resiliência**: Assíncrono por default, com fallbacks, retries e mock para dev.

### 1.2 Escopo e Limitações

- Foco em orquestração, não em treinamento de modelos.
- Suporte inicial a LLMs, visão e ferramentas; extensível via adapters.
- Não inclui execução de código arbitrário (sandboxed para segurança).
- v1.3: Runtime real beta (requer créditos para APIs; fallback mock).

## 2. Arquitetura

### 2.1 Camadas

| Camada     | Componente           | Responsabilidade                                                           |
| ---------- | -------------------- | -------------------------------------------------------------------------- |
| DSL        | SynAI DSL            | Definição de intents, workflows e políticas (step/transform/retry/filter). |
| Runtime    | SynLink Orchestrator | Agendamento async, adapters (Claude/Grok), data flow com fallback.         |
| Bridge     | SynMCP Bridge        | Tradução para protocolos (MCP/xAI/OpenAI prioritários).                    |
| Transports | MCP/HTTP/gRPC/MQTT   | Camada de rede.                                                            |
| Agents     | Implementações       | LLMs (Claude/Grok), Vision (GPT-4V), Tools.                                |

### 2.2 Fluxo de Execução

1. **Parsing**: DSL → AST (via Lark + Transformer).
2. **Weaving**: Resolução semântica (JSONSchema + dependências).
3. **Linking**: Geração de bridges e roteamento (NetworkX com ports).
4. **Runtime**: Execução assíncrona com monitoramento/adapters reais/mock.
5. **Output**: Bytecode `.synx` ou logs/results.

## 3. Sintaxe DSL (v1.3)

orchestrator "demo" {
agents {
grok: LLM { model: "grok-beta" capabilities: ["reason", "code"] }
claude: LLM { model: "claude-3-opus-20240229" capabilities: ["analyze"] }
}
workflow "pipeline" {
start: grok.intent("analyze", input: "data.txt", output: "analysis.json")
connect grok.output -> claude.input { async: false timeout: 10s transform: "json_to_text" retry: 3 filter: "success" }
step: claude.intent("summarize", input: "analysis.json", output: "report.md") # Middle intent
end: claude.intent("finalize")
}
}
run "demo" with workflow "pipeline"

- **Novidades v1.3**: `step:` para intents intermediários, options `transform` (string), `retry` (int), `filter` (string), `async: true/false` (bool).
- **Bool options**: `true/false` como literals.

## 4. Runtime Real (v1.3)

- **Adapters**: LLM → Claude (anthropic SDK) ou Grok (openai compat). Fallback mock se key/créditos inválidos.
- **Data Flow**: Output de intent vira input do próximo via connect; transform aplica funções (mock por enquanto).
- **Error Handling**: Fallback mock + logs (ex.: "Key inválida — regere no console").
- **Async/Retry**: asyncio para parallel, retry baseado em options (beta).

## 5. CLI

- `synai build <file> -o <out> --verbose`: Valida e salva AST.
- `synai link <synx>`: Gera grafo linked.
- `synai run <synx> --real --api-key <key>`: Executa mock/real.

## 6. Limitações v1.3

- Async beta (sem queue full).
- Transforms mock (implemente funções em runtime.py).
- Sem conditions/loops (v2.0).

_SynAI v1.3: Runtime real multi-provider — pronto para produção beta._
