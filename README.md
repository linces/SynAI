# SynAI — A Linguagem de Malha Cognitiva para Orquestração de IA

[![Versão](https://img.shields.io/badge/versão-1.2-azul.svg)](https://github.com/linces/SynAI)
[![Licença](https://img.shields.io/badge/licença-MIT-verde.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-laranja.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-alfa-amarelo.svg)](https://github.com/linces/SynAI)

> 🧠 **SynAI v1.3** — Uma linguagem declarativa para orquestração e colaboração entre agentes de IA, construída para interoperar nativamente com protocolos de contexto como o MCP da Anthropic.


O SynAI é uma linguagem cognitiva declarativa que descreve como inteligências artificiais cooperam para atingir metas, em vez de como elas executam código. Inspirado em anos de experiência em desenvolvimento robusto (de Delphi a Python), este projeto visa criar o "sistema operacional" para redes de IA colaborativas.

SynAI é uma DSL (Domain-Specific Language) declarativa que permite descrever fluxos de colaboração entre IAs heterogêneas de forma simples e modular. Ela abstrai a complexidade de protocolos de comunicação (como MCP, HTTP ou gRPC), focando no "o quê" e "por quê" das interações, em vez do "como".

## Visão Geral

SynAI opera em um nível abstrato acima dos protocolos de transporte. Por exemplo:
- **MCP** (Message Context Protocol da Anthropic) fornece o "fio" de comunicação segura.
- **SynAI** decide o que trafega nesse fio: intents, workflows, goals e políticas de fallback.

Isso cria uma "rede cognitiva" onde IAs de diferentes provedores (Anthropic, OpenAI, Hugging Face) colaboram sem fricções, suportando cenários locais, cloud e edge.

**Por que SynAI?**
- **Interoperabilidade universal**: Conecta modelos via MCP, HTTP, gRPC ou MQTT.
- **Abstração total**: Escreva fluxos declarativos sem lidar com APIs low-level.
- **Segurança e modularidade**: Herda permissões do MCP e permite transportes personalizados.
- **Extensibilidade**: Fácil adaptação para novos protocolos (ex: OpenAI Realtime API).

## Arquitetura de Camadas

SynAI é construída em camadas modulares para escalabilidade:

```
+---------------------------------------------------+
| SYN•AI DSL                                        |
| (Intents, Workflows, Goals, Fallbacks, Policies)  |
+---------------------------------------------------+
| SYN•LINK RUNTIME (Orchestrator)                   |
| (Scheduler, Async Engine, Agent Manager)          |
+---------------------------------------------------+
| SYN•MCP BRIDGE LAYER                              |
| (Adapters, Context Handlers, Message Router)      |
+---------------------------------------------------+
| TRANSPORTS: MCP | HTTP | gRPC | MQTT               |
+---------------------------------------------------+
| AGENT IMPLEMENTATIONS (LLM, Vision, Tools)        |
+---------------------------------------------------+
```

flowchart TD
    A[📜 .synai DSL] --> B[🧩 parse_synai()]
    B -->|gera| C[🌳 AST (árvore sintática)]
    C --> D[✅ build_synai()]
    D -->|valida e enriquece| E[🧠 AST Validado]
    E --> F[🔗 weave_linker()]
    F -->|constrói grafo| G[🔺 Grafo NetworkX]
    G -->|salva| H[💾 .synx bytecode]
    H --> I[▶️ synai run]
    I -->|execução topológica simulada| J[⚙️ Workflow executado]

    classDef parse fill:#dff,stroke:#09f,stroke-width:2px;
    classDef build fill:#dfd,stroke:#090,stroke-width:2px;
    classDef link fill:#ffd,stroke:#990,stroke-width:2px;
    classDef run fill:#fdd,stroke:#900,stroke-width:2px;
    class B,C parse;
    class D,E build;
    class F,G,H link;
    class I,J run;


### Camada de Bridge SynAI-MCP

O bridge traduz elementos SynAI para MCP de forma transparente:
- **Intents** → MCP requests
- **Context metadata** → MCP resource schema
- **Workflow events** → MCP streams

Agentes com `transport: "mcp"` ativam isso automaticamente.

## Exemplo Prático

Aqui vai um workflow simples que usa MCP para um agente textual (Grok via Anthropic), HTTP para geração de imagem e execução local para análise:

```synai
# demo.synai
orchestrator "ColabIA" {
    agents {
        texto: GrokAgent {
            model: "grok-3";
            capabilities: ["nlp", "reasoning"];
            transport: "mcp";  # Integração com MCP
            endpoint: "wss://api.anthropic.com/mcp";
        }

        imagem: DalleAgent {
            model: "dall-e-3";
            capabilities: ["image_gen"];
            transport: "http";
            endpoint: "https://api.openai.com/v1/images";
        }

        analise: LlamaAgent {
            model: "llama-2";
            local: true;
        }
    }

    workflow "VisualReport" {
        start: texto.intent("describe_idea", input: "cidade futurista");

        connect texto.output -> imagem.input {
            transform: embed_to_prompt;
            async: true;
            timeout: 30s;
        }

        connect imagem.output -> analise.input {
            filter: if (imagem.success);
        }

        end: analise.intent("summarize", output: "relatorio_final");
    }

    protocol {
        transport_priority: ["mcp", "http"];
        handshake: "synai-v1.2";
        data_format: "json+embeddings";
    }
}

run "ColabIA" with workflow "VisualReport";
```

**Fluxo explicado:**
- O `GrokAgent` usa MCP para trocar contexto com Claude/Grok.
- O `DalleAgent` chama a API OpenAI via HTTP.
- O `LlamaAgent` processa localmente.
- Tudo orquestrado de forma assíncrona e tolerante a falhas.

### Trecho Técnico do Bridge (Pseudo-Python)

```python
class MCPBridge:
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.socket = None

    async def connect(self):
        self.socket = await websockets.connect(self.endpoint)
        await self.handshake()

    async def handshake(self):
        await self.socket.send(json.dumps({
            "method": "handshake",
            "params": {"protocol": "mcp", "version": "1.0"}
        }))

    async def send_intent(self, intent_name, payload):
        msg = {
            "method": "intent.execute",
            "params": {"name": intent_name, "input": payload}
        }
        await self.socket.send(json.dumps(msg))
        return await self.socket.recv()
```

O runtime SynAI injeta esse bridge quando necessário.

## Benefícios da Integração com MCP

| Benefício              | Explicação                                                                 |
|------------------------|----------------------------------------------------------------------------|
| 🌍 Interoperabilidade universal | Conecta SynAI com Anthropic, OpenAI, HuggingFace, etc.                     |
| 🧱 Abstração total     | Desenvolva fluxos sem conhecer o protocolo subjacente.                     |
| 🛡️ Segurança           | Herda permissões e isolamento do MCP.                                      |
| ⚙️ Modularidade        | Cada agente escolhe o transporte ideal (local, HTTP, MCP, MQTT).           |
| 🧩 Extensibilidade     | Adapte para novos protocolos facilmente.                                   |

## Futuro: SynAI Mesh + MCP Grid

Próximo: Modo **Mesh** para descoberta dinâmica de agentes via service discovery.

```synai
discovery {
    mode: "mesh";
    registry: "synmesh.local";
    protocol_bridge: "mcp";
    match_by: ["capability", "latency", "auth_level"];
}
```

Isso habilita redes distribuídas onde IAs se auto-descobrem e colaboram em tempo real.

## Ecossistema SynAI

### 1. Linguagem e Sintaxe (SynAI DSL)
- Inspirada em YAML + Python: Indentada, legível e declarativa.

### 2. Compilador (SynLink)
Fases:
- **Parsing**: AST via BNF.
- **Semantic Weaving**: Resolve dependências e tipos.
- **Codegen**: Bytecode `.synx` ou código nativo (Python/JS/Rust).

### 3. Linker Cognitivo (SynWeaver)
- Gera bridges automáticos (MCP ↔ HTTP).
- Roteia intents com base em capabilities.
- Cache cognitivo para reuso de respostas.

### 4. Ambiente de Desenvolvimento (SynStudio)
- **IDE**: Syntax highlighting (VSCode plugin).
- **CLI**: `synai build`, `synai run --inspect`, `synai deploy`.
- **Visualização**: Grafos interativos de fluxos.
- **Logs**: "Quem falou com quem, quando e por quê".

### 5. Gramática Formal (BNF) — SynAI v1.2

```
<program> ::= { <declaration> }

<declaration> ::= <orchestrator_decl> | <agent_decl> | <workflow_decl> | <protocol_decl> | <run_decl>

<orchestrator_decl> ::= "orchestrator" <string> "{" { <block> } "}"

<block> ::= <agents_block> | <workflow_block> | <protocol_block>

<agents_block> ::= "agents" "{" { <agent_entry> } "}"

<agent_entry> ::= <id> ":" <agent_type> "{" { <agent_property> } "}"

<agent_property> ::= "model" ":" <string>
                   | "capabilities" ":" "[" { <string> [","] } "]"
                   | "endpoint" ":" <string>
                   | "transport" ":" <string>
                   | "local" ":" "true"
                   | "auth" ":" <string>

<workflow_block> ::= "workflow" <string> "{" { <workflow_stmt> } "}"

<workflow_stmt> ::= <intent_stmt> | <connect_stmt> | <end_stmt>

<intent_stmt> ::= <id> "." "intent" "(" <string> ["," "input:" <value>] ")"

<connect_stmt> ::= "connect" <id> "." "output" "->" <id> "." "input" "{" { <connect_opt> } "}"

<connect_opt> ::= "transform:" <id> | "async:" "true" | "timeout:" <time> | "filter:" <expr>

<end_stmt> ::= "end:" <id> "." "intent" "(" <string> ["," "output:" <id>] ")"

<protocol_block> ::= "protocol" "{" { <proto_property> } "}"

<proto_property> ::= "handshake:" <string>
                   | "data_format:" <string>
                   | "error_handling:" <string>
                   | "transport_priority:" "[" { <string> [","] } "]"

<run_decl> ::= "run" <string> "with" "workflow" <string>

<id> ::= /[A-Za-z_][A-Za-z0-9_]*/
<string> ::= "\"" [^"]* "\""
<value> ::= <string> | <number> | <bool> | <list> | <object>
<time> ::= <number> "s" | <number> "ms"
```

### 6. Exemplo de Compilação

**Entrada** (`demo.synai`):
```synai
orchestrator "Demo" {
    agents {
        texto: GrokAgent {
            model: "grok-3";
            capabilities: ["nlp"];
            transport: "mcp";
        }
        resumo: LlamaAgent {
            local: true;
        }
    }

    workflow "ResumoDeTexto" {
        start: texto.intent("analyze", input: "Resumo de IA declarativa");
        connect: texto.output -> resumo.input {
            async: true;
        }
        end: resumo.intent("summarize", output: "relatorio");
    }
}

run "Demo" with workflow "ResumoDeTexto";
```

**Saída** (`.synx` — Bytecode intermediário):
```json
{
  "version": "1.2",
  "orchestrator": "Demo",
  "workflow": "ResumoDeTexto",
  "agents": [
    {"id": "texto", "model": "grok-3", "transport": "mcp"},
    {"id": "resumo", "model": "llama", "local": true}
  ],
  "links": [
    {"from": "texto.output", "to": "resumo.input", "async": true}
  ],
  "intents": [
    {"agent": "texto", "action": "analyze"},
    {"agent": "resumo", "action": "summarize"}
  ]
}
```

## Ciclo de Vida de um Projeto

1. `.synai` → **SynLink Compiler** → `.synx` bytecode
2. **SynWeaver** + **SynStudio** → Runtime execution
3. Deploy para Mesh (local/cloud)

## ⚙️ Roadmap de Implementação

| Etapa | Descrição | Status |
|-------|-----------|--------|
| 🔹 Gramática BNF | Base sintática e parser inicial (Lark/TextX) | Próximo passo |
| 🔹 AST & Type system | Tipagem leve para intents e agents | Planejado |
| 🔹 Codegen Python | Gerador para runtime local | Próximo |
| 🔹 SynWeaver | Linker de fluxos (async + retries + bridge MCP) | Depois |
| 🔹 SynStudio | IDE/CLI com visualização | Fase 2 |

## Instalação

1. Clone o repositório:
   ```bash:disable-run
   git clone https://github.com/linces/SynAI.git
   cd SynAI
   ```

2. Instale dependências (Python 3.8+):
   ```bash
   pip install -r requirements.txt  # Inclui Lark, websockets, etc.
   ```

3. Compile um exemplo:
   ```bash
   synai build demo.synai
   synai run demo.synx
   ```

## Contribuições

- Faça fork do repositório e crie uma branch.
- Submeta PRs com testes.
- Discuta issues no [GitHub Discussions](https://github.com/linces/SynAI/discussions).

**Contato:** Para colaborações ou suporte, entre em contato via [linces@gmail.com](mailto:linces@gmail.com) ou [WhatsApp](https://wa.me/+5534999623545).

## 📄 Licença

MIT License — veja [LICENSE](LICENSE).

## Agradecimentos

Inspirado em café em conversas com alguns loucos aqui, e conversas colaborativas com IAs como Grok, Claude, ChatGPT e anos de experiência em desenvolvimento de software robusto (Delphi, Python, APIs). SynAI + MCP: a simbiose perfeita para o futuro da colaboração entre IAs!

---

*SynAI: O sistema operacional para redes cognitivas.*
```
