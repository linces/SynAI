import asyncio
from typing import Dict, Any, Optional
import anthropic
import openai
import google.generativeai as genai
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

    def __init__(self, api_key: Optional[str] = None, xai_key: Optional[str] = None, google_key: Optional[str] = None, real: bool = False):
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

        # Configuração Gemini (Google)
        g_key = google_key or os.getenv('GOOGLE_API_KEY')
        self.client_gemini = False
        if g_key:
            try:
                genai.configure(api_key=g_key)
                self.client_gemini = True
                print("[SynAI] ✅ Gemini (Google) key carregada.")
            except Exception as e:
                print(f"[SynAI] ❌ Erro ao inicializar Gemini: {e}")

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

                # Determinar input (Prioridade: 1. Variável | 2. Literal no DSL | 3. Conexão direta)
                dsl_input = stmt.get('input', 'N/A')
                connected_input = data_flow.get(f"{agent_id}_input")
                
                if dsl_input in data_flow:
                    input_data = data_flow[dsl_input]
                elif dsl_input != 'N/A' and dsl_input != agent_id:
                    input_data = dsl_input
                elif connected_input:
                    input_data = connected_input
                else:
                    input_data = dsl_input

                print(f"🎯 Executando intent {agent_id}.{stmt['name']} (input: {input_data})")

                res_type = agent_cfg['properties'].get('agent_type', agent_cfg.get('agent_type', 'LLM'))
                resolved_type = str(res_type).replace('"', '').upper()
                if (mock or not self.real) and resolved_type != 'TOOL':
                    output = f"mock_result_{stmt['name']}({input_data})"
                else:
                    output = await self._dispatch_to_adapter(agent_cfg, stmt, input_data)

                # Salvar output (no ID do agente para retrocompatibilidade e no nome da variável se existir)
                data_flow[f"{agent_id}_output"] = output
                if stmt.get('output'):
                    data_flow[stmt['output']] = output
                    
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
        res_type = agent_cfg['properties'].get('agent_type', agent_cfg.get('agent_type', 'LLM'))
        agent_type = str(res_type).replace('"', '').upper()
        adapter = self.adapters.get(agent_type)
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
        res_func = config['properties'].get('function', intent['name'])
        tool_name = str(res_func).replace('"', '')
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
        return await self.call_model(model, prompt, max_tokens=512, endpoint=endpoint)

    # ------------------------------------------------------------------------
    # CHAMADA DIRETA DE MODELO (Public API)
    # ------------------------------------------------------------------------
    async def call_model(self, model: str, prompt: str, max_tokens: int = 1024, endpoint: str = "") -> str:
        """Invoca um LLM diretamente com prompt e modelo."""
        print(f"🧠 Executando LLM ({model}){' → ' + endpoint if endpoint else ''}")

        # xAI Grok
        if 'grok' in model.lower():
            if self.client_grok:
                try:
                    response = self.client_grok.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens
                    )
                    out = response.choices[0].message.content or "(sem resposta)"
                    print(f"💾 Resposta Grok ({len(out)} chars)")
                    return out
                except Exception as e:
                    print(f"⚠️  Erro xAI ({model}): {e}")
                    return f"grok_mock (erro: {e})"
            else:
                print(f"❌ Erro: Modelo '{model}' solicitado mas XAI_API_KEY não configurada.")
                return f"error: missing xai key for {model}"

        # Gemini (Google)
        elif 'gemini' in model.lower():
            if self.client_gemini:
                try:
                    gen_model = genai.GenerativeModel(model)
                    response = gen_model.generate_content(prompt)
                    out = response.text or "(sem resposta)"
                    print(f"💾 Resposta Gemini ({len(out)} chars)")
                    return out
                except Exception as e:
                    print(f"⚠️ Erro Gemini ({model}): {e}")
                    return f"gemini_mock ({e})"
            else:
                print(f"❌ Erro: Modelo '{model}' solicitado mas GOOGLE_API_KEY não configurada.")
                return f"error: missing google key for {model}"

        # Anthropic Claude
        elif 'claude' in model.lower() or self.client_anthro:
            if self.client_anthro:
                try:
                    msg = self.client_anthro.messages.create(
                        model=model if 'claude' in model.lower() else "claude-3-haiku-20240307",
                        max_tokens=max_tokens,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    out = msg.content[0].text if msg.content else "(vazio)"
                    print(f"💾 Resposta Claude ({len(out)} chars)")
                    return out
                except Exception as e:
                    print(f"⚠️ Erro Claude ({model}): {e}")
                    return f"claude_mock ({e})"
            else:
                print(f"❌ Erro: Modelo '{model}' solicitado mas ANTHROPIC_API_KEY não configurada.")
                return f"error: missing anthropic key for {model}"

        else:
            print(f"⚠️ Nenhuma API configurada para o modelo '{model}' — fallback mock.")
            return f"mock_result({model})"

    # ------------------------------------------------------------------------
    # GERAÇÃO DE EMBEDDINGS (RAG Support)
    # ------------------------------------------------------------------------
    async def get_embedding(self, text: str, model: str = "models/text-embedding-004") -> Optional[list]:
        """Gera um vetor de embedding para o texto fornecido."""
        if not self.client_gemini:
            print("❌ Erro: get_embedding falhou. Gemini não configurado.")
            return None
        
        try:
            result = genai.embed_content(
                model=model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"⚠️ Erro ao gerar embedding: {e}")
            return None


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
