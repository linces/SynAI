import asyncio
from typing import Dict, Any, Optional
import anthropic
import openai
import os
import json
from dotenv import load_dotenv

# Carrega .env automaticamente
load_dotenv()

class SynRuntime:
    """
    Núcleo de execução do SynAI.
    Gerencia runtime, comunicação entre agentes e execução de intents.
    """

    def __init__(self, api_key: Optional[str] = None, xai_key: Optional[str] = None, real: bool = False):
        self.real = real
        self.adapters = {
            'LLM': self._llm_adapter,
            'TOOL': self._tool_adapter,
        }
        self.tools: Dict[str, Any] = {}

        # Configuração Anthropic
        anthro_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.client_anthro = None
        if anthro_key:
            try:
                self.client_anthro = anthropic.Anthropic(api_key=anthro_key)
                # Teste básico de validade
                try:
                    self.client_anthro.messages.create(
                        model="claude-3-opus-20240229",
                        max_tokens=1,
                        messages=[{"role": "user", "content": "ping"}]
                    )
                    print("[SynAI] ✅ Anthropic key validada.")
                except Exception:
                    print("[SynAI] ⚠️ Anthropic inicializado (sem teste de ping).")
            except Exception as e:
                print(f"[SynAI] ❌ Erro ao inicializar Anthropic: {e}")

        # Configuração xAI (Grok)
        xai_key = xai_key or os.getenv('XAI_API_KEY')
        self.client_grok = None
        if xai_key:
            try:
                self.client_grok = openai.OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1")
                print("[SynAI] ✅ xAI (Grok) key carregada.")
            except Exception as e:
                print(f"[SynAI] ❌ Erro ao inicializar xAI: {e}")

    # ------------------------------------------------------------------------
    # EXECUÇÃO DE WORKFLOW
    # ------------------------------------------------------------------------
    async def execute_workflow(self, ast: Dict[str, Any], run_decl: Dict[str, Any], mock: bool = True) -> Dict[str, Any]:
        """Executa um workflow SynAI completo (se real=False, roda mock)."""
        orch_name = run_decl['orchestrator']
        wf_name = run_decl['workflow']

        orch = next((d for d in ast['declarations']
                     if d['type'] == 'Orchestrator' and d['name'] == orch_name), None)
        if not orch:
            raise ValueError(f"❌ Orchestrator '{orch_name}' não encontrado no AST.")

        wf = next((b for b in orch['blocks']
                   if b['type'] == 'Workflow' and b['name'] == wf_name), None)
        if not wf:
            raise ValueError(f"❌ Workflow '{wf_name}' não encontrado no Orchestrator '{orch_name}'.")

        data_flow = {}
        results = []
        print(f"🚀 Iniciando execução do workflow '{wf_name}' de '{orch_name}' (modo real: {self.real})")

        for stmt in wf['statements']:
            stmt_type = stmt['type']

            # -------------------------------
            # INTENT (execução de agente)
            # -------------------------------
            if stmt_type == 'Intent':
                agent_id = stmt['agent']
                agent_cfg = self._get_agent_config(orch, agent_id)
                if not agent_cfg:
                    print(f"⚠️  Agente '{agent_id}' não encontrado — ignorando intent '{stmt['name']}'")
                    continue

                input_data = data_flow.get(f"{agent_id}_input", stmt.get('input', 'N/A'))
                print(f"🎯 Executando intent {agent_id}.{stmt['name']} (input: {input_data})")

                if (mock or not self.real) and agent_cfg.get('agent_type') != 'TOOL':
                    output = f"mock_result_{stmt['name']}({input_data})"
                else:
                    output = await self._dispatch_to_adapter(agent_cfg, stmt, input_data)

                data_flow[f"{agent_id}_output"] = output
                results.append({'intent': stmt['name'], 'agent': agent_id, 'output': output})

            # -------------------------------
            # CONNECT (ligação de agentes)
            # -------------------------------
            elif stmt_type == 'Connect':
                from_agent = stmt['from']
                to_agent = stmt['to']
                opts = stmt.get('options', {})
                from_data = data_flow.get(f"{from_agent}_output", 'N/A')
                data_flow[f"{to_agent}_input"] = from_data
                print(f"🔗 Conectando {from_agent}.output → {to_agent}.input (data: {from_data}, options: {opts})")

                # Controle de tempo/async
                if opts.get('async'):
                    await asyncio.sleep(0.05)
                if opts.get('timeout'):
                    await asyncio.sleep(min(0.1, opts['timeout'] / 100))

            else:
                print(f"⚠️ Tipo de instrução '{stmt_type}' desconhecido — ignorado.")

        print("✅ Execução concluída com sucesso.")
        return {'status': 'completed', 'results': results, 'flow': data_flow}

    # ------------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------------
    def _get_agent_config(self, orch: Dict[str, Any], agent_id: str) -> Optional[Dict[str, Any]]:
        """Retorna o bloco de configuração de um agente pelo ID."""
        for block in orch.get('blocks', []):
            if block['type'] == 'AgentsBlock':
                for agent in block['agents']:
                    if agent['id'] == agent_id:
                        return agent
        return None

    async def _dispatch_to_adapter(self, agent_cfg: Dict[str, Any], intent: Dict[str, Any], input_data: str) -> str:
        """Envia execução ao adapter certo (baseado no tipo de agente)."""
        # Priorizar agent_type definido nas propriedades, senao usar o AGENT_TYPE do DSL
        agent_type = agent_cfg['properties'].get('agent_type', agent_cfg.get('agent_type', 'LLM'))
        adapter = self.adapters.get(agent_type.upper())
        if not adapter:
            print(f"⚠️  Adapter '{agent_type}' não implementado — fallback mock.")
            return f"mock_result_{intent['name']}({input_data})"
        return await adapter(agent_cfg, intent, input_data)

    # ------------------------------------------------------------------------
    # FERRAMENTAS (Tools)
    # ------------------------------------------------------------------------
    def register_tool(self, name: str, func: Any):
        """Registra uma função Python como ferramenta executável."""
        self.tools[name] = func
        print(f"[SynAI] 🛠️  Ferramenta registrada: {name}")

    async def _tool_adapter(self, config: Dict[str, Any], intent: Dict[str, Any], input_data: str) -> str:
        """Adapter para execução de ferramentas locais."""
        tool_name = config['properties'].get('function', intent['name'])
        print(f"🛠️  Executando Ferramenta: {tool_name}({input_data})")
        
        if tool_name in self.tools:
            try:
                func = self.tools[tool_name]
                if asyncio.iscoroutinefunction(func):
                    result = await func(input_data)
                else:
                    result = func(input_data)
                return str(result)
            except Exception as e:
                return f"Erro na execução da ferramenta {tool_name}: {e}"
        else:
            return f"Erro: Ferramenta '{tool_name}' não registrada no runtime."

    # ------------------------------------------------------------------------
    # ADAPTADOR LLM (Anthropic, xAI)
    # ------------------------------------------------------------------------
    async def _llm_adapter(self, config: Dict[str, Any], intent: Dict[str, Any], input_data: str) -> str:
        """Adapter genérico para LLMs (Claude, Grok, etc)."""
        model = config['properties'].get('model', 'unknown')
        endpoint = config['properties'].get('endpoint', '')
        prompt = f"Tarefa: {intent['name']}\nInput: {input_data}\nFormato de saída: {intent.get('output', 'texto')}."
        print(f"🧠 Executando LLM {config['id']} ({model}) → endpoint: {endpoint}")

        # xAI Grok
        if 'grok' in model.lower() and self.client_grok:
            try:
                response = self.client_grok.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512
                )
                out = response.choices[0].message.content or "(sem resposta)"
                print(f"💾 Resposta Grok ({len(out)} chars)")
                return out
            except Exception as e:
                print(f"⚠️  Erro xAI ({model}): {e}")
                return f"grok_mock_{intent['name']} (erro: {e})"

        # Anthropic Claude
        elif self.client_anthro:
            try:
                msg = self.client_anthro.messages.create(
                    model=model,
                    max_tokens=512,
                    messages=[{"role": "user", "content": prompt}]
                )
                out = msg.content[0].text if msg.content else "(vazio)"
                print(f"💾 Resposta Claude ({len(out)} chars)")
                return out
            except anthropic.BadRequestError as e:
                if "credit balance" in str(e):
                    print("💸 Créditos insuficientes Anthropic.")
                    return f"claude_mock_{intent['name']} (sem créditos)"
                elif "invalid x-api-key" in str(e):
                    print("🔑 Key Anthropic inválida.")
                    return f"claude_mock_{intent['name']} (key inválida)"
                else:
                    print(f"⚠️ Erro Claude: {e}")
                    return f"claude_mock_{intent['name']} ({e})"
            except Exception as e:
                print(f"⚠️ Erro inesperado Claude: {e}")
                return f"claude_mock_{intent['name']} ({e})"

        else:
            print("⚠️ Nenhuma API configurada — fallback mock.")
            return f"mock_result_{intent['name']}({input_data})"


# ------------------------------------------------------------------------
# EXECUÇÃO DIRETA DE TESTE
# ------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if not os.path.exists(path):
            print(f"❌ Arquivo {path} não encontrado.")
            exit(1)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        runtime = SynRuntime(real=True)
        result = asyncio.run(runtime.execute_workflow(
            data['validated_ast'],
            next(d for d in data['validated_ast']['declarations'] if d['type'] == 'Run'),
            mock=False
        ))
        print(json.dumps(result, indent=2, ensure_ascii=False))
