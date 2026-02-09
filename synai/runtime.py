import asyncio
from typing import Dict, Any, Optional
import os
import json
from dotenv import load_dotenv
from .interfaces import LLMProvider

# Carrega .env automaticamente
load_dotenv()

class SynRuntime:
    """
    Núcleo de execução do SynAI (Versão Agnóstica).
    Gerencia runtime, comunicação entre agentes e execução de intents via Drivers.
    """

    def __init__(self, real: bool = False):
        self.real = real
        self.adapters = {
            'LLM': self._llm_adapter,
            'TOOL': self._tool_adapter,
        }
        self.tools: Dict[str, Any] = {}
        self.llm_providers: Dict[str, LLMProvider] = {}
        self.default_provider: Optional[str] = None

    def register_llm_provider(self, alias: str, provider: LLMProvider, set_default: bool = False):
        """Registra um driver de LLM (ex: 'anthropic', 'openai', 'local')."""
        self.llm_providers[alias] = provider
        if set_default or not self.default_provider:
            self.default_provider = alias
        print(f"[SynAI] 🧠 Driver de LLM registrado: {alias}")

    # ------------------------------------------------------------------------
    # EXECUÇÃO DE WORKFLOW
    # ------------------------------------------------------------------------
    async def execute_workflow(self, ast: Dict[str, Any], run_decl: Dict[str, Any], mock: bool = True) -> Dict[str, Any]:
        """Executa um workflow SynAI completo."""
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

                # Resolver input
                raw_input = stmt.get('input', '')
                input_data = self._resolve_input(raw_input, data_flow)

                print(f"⚡ Executing intent: {stmt['name']} ({agent_id})")
                
                # Dispatch para Adapter
                result = await self._dispatch_to_adapter(agent_cfg, stmt, input_data)
                
                # Armazenar resultado
                results.append({'intent': stmt['name'], 'result': result})
                data_flow[stmt['name']] = result

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

    def _resolve_input(self, raw_input: Any, data_flow: Dict[str, Any]) -> str:
        """Resolve referências como result('IntentName')."""
        if isinstance(raw_input, str) and raw_input.startswith("result(") and raw_input.endswith(")"):
            target_intent = raw_input[7:-1].replace('"', '').replace("'", "")
            return data_flow.get(target_intent, f"(resultado de {target_intent} não encontrado)")
        return str(raw_input)

    async def _dispatch_to_adapter(self, agent_cfg: Dict[str, Any], intent: Dict[str, Any], input_data: str) -> str:
        """Envia execução ao adapter certo (baseado no tipo de agente)."""
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

    def register_toolkit(self, toolkit: Dict[str, Any]):
        """Registra um dicionário inteiro de ferramentas."""
        for name, func in toolkit.items():
            self.register_tool(name, func)

    async def _tool_adapter(self, config: Dict[str, Any], intent: Dict[str, Any], input_data: str) -> str:
        """Adapter para execução de ferramentas locais."""
        res_func = config.get('properties', {}).get('function', intent['name'])
        tool_name = str(res_func).replace('"', '')
        
        print(f"🛠️  [SynAI] Executando Tool: {tool_name}({input_data[:50]}...)")
        
        if tool_name in self.tools:
            try:
                func = self.tools[tool_name]
                if asyncio.iscoroutinefunction(func):
                    result = await func(input_data)
                else:
                    result = func(input_data)
                return str(result)
            except Exception as e:
                err_msg = f"Erro na execução da ferramenta {tool_name}: {str(e)}"
                print(f"❌ [SynAI] {err_msg}")
                return err_msg
        else:
            warn_msg = f"Aviso: Ferramenta '{tool_name}' não registrada no runtime."
            print(f"⚠️  [SynAI] {warn_msg}")
            return warn_msg

    # ------------------------------------------------------------------------
    # ADAPTADOR LLM (Via Drivers)
    # ------------------------------------------------------------------------
    async def _llm_adapter(self, config: Dict[str, Any], intent: Dict[str, Any], input_data: str) -> str:
        """Adapter que delega para o Driver LLM adequado."""
        model_name = config['properties'].get('model', 'unknown')
        # Provider pode ser especificado na config do agente ou inferido
        provider_alias = config['properties'].get('provider', self.default_provider)
        
        if not provider_alias or provider_alias not in self.llm_providers:
            # Fallback inteligente: tenta inferir pelo nome do modelo se o provider não for explícito
            if "claude" in model_name: provider_alias = "anthropic"
            elif "gpt" in model_name or "grok" in model_name: provider_alias = "openai"
            elif "gemini" in model_name: provider_alias = "google"
        
        driver = self.llm_providers.get(provider_alias)
        
        if not driver:
             if not self.real:
                 return f"MOCK_LLM_RESPONSE({model_name}): {input_data}"
             return f"Erro: Nenhum driver LLM encontrado para '{provider_alias}' (modelo: {model_name})"

        prompt = f"Tarefa: {intent['name']}\nInput: {input_data}\nFormato de saída: {intent.get('output', 'texto')}."
        
        print(f"🧠 [SynAI] Invocando Driver '{provider_alias}' para modelo '{model_name}'")
        try:
            return await driver.generate(prompt=prompt, model=model_name)
        except Exception as e:
            print(f"❌ [SynAI] Erro no driver {provider_alias}: {e}")
            return f"Erro de geração: {e}"

    async def get_embedding(self, text: str) -> Optional[list[float]]:
        """Gera embedding usando o driver padrão ou o primeiro disponível."""
        driver = self.llm_providers.get(self.default_provider)
        if driver:
            try:
                return await driver.get_embedding(text)
            except Exception as e:
                print(f"⚠️ Falha ao gerar embedding: {e}")
        return None

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

                # Dispatch para Adapter
                result = await self._dispatch_to_adapter(agent_cfg, stmt, input_data)

                # Armazenar resultado
                data_flow[f"{agent_id}_output"] = result
                if stmt.get('output'):
                    data_flow[stmt['output']] = result
                    
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
    # ------------------------------------------------------------------------
    # FERRAMENTAS (Tools)
    # ------------------------------------------------------------------------
    def register_tool(self, name: str, func: Any):
        """Registra uma função Python como ferramenta executável."""
        self.tools[name] = func
        print(f"[SynAI] 🛠️  Ferramenta registrada: {name}")

    def register_toolkit(self, toolkit: Dict[str, Any]):
        """Registra um dicionário inteiro de ferramentas."""
        for name, func in toolkit.items():
            self.register_tool(name, func)

    async def _tool_adapter(self, config: Dict[str, Any], intent: Dict[str, Any], input_data: str) -> str:
        """Adapter para execução de ferramentas locais."""
        # Tenta pegar o nome da função da propriedade 'function' ou usa o nome do intent
        res_func = config.get('properties', {}).get('function', intent['name'])
        tool_name = str(res_func).replace('"', '')
        
        print(f"🛠️  [SynAI] Executando Tool: {tool_name}({input_data[:50]}...)")
        
        if tool_name in self.tools:
            try:
                func = self.tools[tool_name]
                if asyncio.iscoroutinefunction(func):
                    result = await func(input_data)
                else:
                    result = func(input_data)
                return str(result)
            except Exception as e:
                err_msg = f"Erro na execução da ferramenta {tool_name}: {str(e)}"
                print(f"❌ [SynAI] {err_msg}")
                return err_msg
        else:
            warn_msg = f"Aviso: Ferramenta '{tool_name}' não registrada no runtime."
            print(f"⚠️  [SynAI] {warn_msg}")
            return warn_msg

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
        """Invoca um LLM diretamente usando os Drivers registrados."""
        print(f"🧠 [SynAI] Call Model direto: {model}")
        
        # Determinar provider
        provider_alias = self.default_provider
        if "claude" in model.lower(): provider_alias = "anthropic"
        elif "gpt" in model.lower() or "grok" in model.lower(): provider_alias = "openai"
        elif "gemini" in model.lower(): provider_alias = "google"
        
        driver = self.llm_providers.get(provider_alias)
        
        if not driver:
            if not self.real:
                return f"MOCK_DIRECT_RESPONSE({model}): {prompt[:20]}..."
            return f"Erro: Driver não encontrado para modelo '{model}' (Provider: {provider_alias})"

        try:
            # Chama o driver de forma assíncrona
            return await driver.generate(prompt=prompt, model=model, max_tokens=max_tokens)
        except Exception as e:
            print(f"❌ [SynAI] Erro em call_model ({provider_alias}): {e}")
            return f"Error executing {model}: {e}"

    # ------------------------------------------------------------------------
    # GERAÇÃO DE EMBEDDINGS (RAG Support)
    # ------------------------------------------------------------------------
    async def get_embedding(self, text: str, model: str = "models/gemini-embedding-001") -> Optional[list]:
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
