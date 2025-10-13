# SynAI v1.2 -- Documento Tecnico Completo

## 1. Introducao

### 1.1 Visao Geral
SynAI é uma linguagem de programacao declarativa projetada especificamente para orquestracao de agentes de IA heterogeneos. Ela abstrai protocolos de comunicacao subjacentes (ex: MCP da Anthropic, HTTP, gRPC) para permitir fluxos colaborativos simples e escalaveis. Versao 1.2 introduz suporte nativo ao MCP como "dialeto base" para interacoes contextuais seguras.

**Principios Fundamentais:**
- **Declaratividade**: Descreva *o que* as IAs devem alcancar, nao *como* implementa-lo.
- **Interoperabilidade**: Suporte a multiplos transportes sem boilerplate.
- **Modularidade**: Agentes plugaveis com capabilities declaradas.
- **Resiliencia**: Assincrono por default, com fallbacks e retries.

### 1.2 Escopo e Limitacoes
- Foco em orquestracao, nao em treinamento de modelos.
- Suporte inicial a LLMs, visao e ferramentas; extensivel via adapters.
- Nao inclui execucao de codigo arbitrario (sandboxed para seguranca).

## 2. Arquitetura

### 2.1 Camadas
| Camada | Componente | Responsabilidade |
|--------|------------|------------------|
| DSL | SynAI DSL | Definicao de intents, workflows e politicas. |
| Runtime | SynLink Orchestrator | Agendamento, engine async e gerenciamento de agentes. |
| Bridge | SynMCP Bridge | Traducao para protocolos (MCP prioritario). |
| Transports | MCP/HTTP/gRPC/MQTT | Camada de rede. |
| Agents | Implementacoes | LLMs (Grok, Claude), Vision (DALL-E), Tools. |

### 2.2 Fluxo de Execucao
1. **Parsing**: DSL --> AST (via Lark parser).
2. **Weaving**: Resolucao semantica (tipos, dependencias).
3. **Linking**: Geracao de bridges e roteamento.
4. **Runtime**: Execucao assincrona com monitoramento.
5. **Output**: Bytecode `.synx` ou execucao direta.

[Full spec - paste complete from previous for production]
