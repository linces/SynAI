# SynAI: The Sovereign Intelligence Language ☀️🚀💎

SynAI é uma DSL (Domain Specific Language) projetada para orquestrar Inteligência Artificial de forma declarativa e agnóstica.

## 🏛️ Filosofia

O SynAI separa o **QUÊ** (Intenção) do **COMO** (Implementação).

- **SuperAgente**: É o _runtime_ que executa SynAI.
- **LifeOS**: É um dos _produtos_ construídos com SynAI.

## 📜 Sintaxe Básica

### 1. Definição de Agentes (Personas)

```synai
agent "Lince-Analyst" {
    agent_type: "LLM"
    model: "claude-3-5-sonnet-20240620"
    system_prompt: "Você é um analista de mercado de elite."
}
```

### 2. Orquestração de Fluxo (Workflows)

```synai
orchestrator "Market_Research_V1" {

    workflow "Analyze_Competitor" {
        intent "Coletar Dados" {
            agent: "Lince-NetSec"
            function: "web_search"
            input: "Preços do concorrente X"
        }

        intent "Gerar Relatório" {
            agent: "Lince-Analyst"
            input: result("Coletar Dados")
        }
    }
}
```

## 🛠️ Usage (Python)

```python
from synai import SynRuntime

# 1. Inicializar Runtime
rt = SynRuntime(real=True)

# 2. Registrar Ferramentas Locais
def my_tool(x): return x * 2
rt.register_tool("double", my_tool)

# 3. Carregar e Executar Arquivo .synai
# ... (parser logic)
```
