import asyncio
from typing import Dict, Any, Optional, List, Callable
import os
import json
from dotenv import load_dotenv
from .interfaces import LLMProvider
from .profiles import is_profile, resolve_model, get_profile_models, MODEL_PROFILES
from .router import RouterEngine, ZERO_COST_POLICIES, FREE_BLOCKED_PROVIDERS

load_dotenv()

# FALLBACK_CHAIN legado mantido para compatibilidade retroativa.
# Internamente o SynRuntime usa RouterEngine.get_chain(policy) agora.
# Equivale à política "balanced" (OpenRouter como hub central).
FALLBACK_CHAIN: List[str] = RouterEngine.get_chain("balanced")


def _infer_provider(model: str) -> Optional[str]:
    """
    Infere o provider correto pelo nome/slug do modelo.
    Usado pelo call_model quando 'provider' não está explícito.
    """
    m = model.lower()
    if "gemini" in m:       return "google"
    if "/" in m:            return "openrouter"
    if "claude" in m:       return "anthropic"
    if "gpt" in m:          return "openai"
    if "deepseek" in m:     return "deepseek"
    if "grok" in m:         return "grok"
    if "qwen" in m:         return "openrouter"
    if "mistral" in m:      return "openrouter"
    if "codestral" in m:    return "openrouter"
    if "llama" in m:        return "groq"
    if "mixtral" in m:      return "groq"
    if "gemma" in m:        return "groq"
    return None


class SynRuntime:
    """
    Núcleo de execução do SynAI (Versão Agnóstica Multi-Provider).

    Gerencia o registry de providers, a cadeia de fallback automática,
    a execução de workflows DSL e o dispatcher de ferramentas.
    """

    def __init__(self, real: bool = False, policy: str = "balanced"):
        self.real = real
        self.policy = RouterEngine.validate_policy(policy) or "balanced"
        self.adapters = {
            'LLM': self._llm_adapter,
            'TOOL': self._tool_adapter,
        }
        self.tools: Dict[str, Any] = {}
        self.llm_providers: Dict[str, LLMProvider] = {}
        self.default_provider: Optional[str] = None
        self.event_listeners: List[Callable[[str, Dict[str, Any]], None]] = []

        print(f"[SynAI] Politica de roteamento: '{self.policy}' - {RouterEngine.describe_policy(self.policy)}")

        if real:
            # Auto-registra todos os 8 drivers padrão do SynAI v1.6
            from synai.providers import (
                DeepSeekDriver, OpenRouterDriver, GroqDriver, OllamaDriver,
                GrokDriver, GoogleDriver, OpenAIDriver, AnthropicDriver
            )
            # Ativar prefer_free no OpenRouter quando a política for zero-cost
            prefer_free = self.policy in ZERO_COST_POLICIES
            self.register_llm_provider("deepseek", DeepSeekDriver())
            self.register_llm_provider("openrouter", OpenRouterDriver(prefer_free=prefer_free))
            self.register_llm_provider("groq", GroqDriver())
            self.register_llm_provider("ollama", OllamaDriver())
            self.register_llm_provider("grok", GrokDriver())
            self.register_llm_provider("google", GoogleDriver())
            self.register_llm_provider("openai", OpenAIDriver())
            self.register_llm_provider("anthropic", AnthropicDriver())

    def add_event_listener(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Registra um callback para telemetria de roteamento."""
        self.event_listeners.append(callback)

    def _dispatch_event(self, event_name: str, payload: Dict[str, Any]):
        """Dispara um evento de telemetria para todos os listeners."""
        for listener in self.event_listeners:
            try:
                listener(event_name, payload)
            except Exception as e:
                print(f"[SynAI][Telemetry] Erro ao disparar evento '{event_name}': {e}")

    def set_policy(self, policy: str) -> bool:
        """
        Altera a política de roteamento em tempo de execução.

        Args:
            policy: Nome da nova política ("free", "balanced", "premium", etc.)

        Returns:
            True se a política foi aceita, False se inválida.
        """
        validated = RouterEngine.validate_policy(policy)
        if not validated:
            print(f"[SynAI] Politica '{policy}' invalida. Mantendo '{self.policy}'.")
            return False
        self.policy = validated
        print(f"[SynAI] Politica alterada para '{self.policy}' - {RouterEngine.describe_policy(self.policy)}")
        # Atualizar prefer_free no driver OpenRouter se registrado
        or_driver = self.llm_providers.get("openrouter")
        if or_driver and hasattr(or_driver, 'prefer_free'):
            or_driver.prefer_free = self.policy in ZERO_COST_POLICIES
        return True

    def _is_allowed_by_policy(self, provider: str) -> bool:
        """Verifica se o provider é permitido pela política ativa."""
        return RouterEngine.is_provider_allowed(provider, self.policy)

    def _build_candidate_chain(
        self,
        preferred_provider: Optional[str] = None,
        inferred: Optional[str] = None,
    ) -> List[str]:
        """
        Monta a lista final de providers candidatos para uma chamada.

        Ordem:
            1. Provider explícito (respeitado mesmo sendo premium, exceto em zero-cost)
            2. Provider inferido pelo modelo
            3. Provider padrão
            4. Cadeia completa da política ativa

        Em políticas zero-cost (free/cheapest/local), providers pagos são
        removidos da lista mesmo se especificados explicitamente.
        """
        seen: set = set()
        candidates: List[str] = []

        def _add(alias: Optional[str]):
            if alias and alias not in seen and self._is_allowed_by_policy(alias):
                seen.add(alias)
                candidates.append(alias)

        _add(preferred_provider)
        _add(inferred)
        _add(self.default_provider)
        for p in RouterEngine.get_chain(self.policy):
            _add(p)

        return candidates


    # ─────────────────────────────────────────────────────────────────────────
    # REGISTRO DE PROVIDERS
    # ─────────────────────────────────────────────────────────────────────────
    def register_llm_provider(self, alias: str, provider: LLMProvider, set_default: bool = False):
        """
        Registra um driver de LLM pelo alias (ex: 'deepseek', 'openrouter').

        Args:
            alias:       Identificador usado no registry e no fallback chain.
            provider:    Instância do driver (deve implementar LLMProvider).
            set_default: Se True, este provider vira o padrão para call_model.
        """
        self.llm_providers[alias] = provider
        if set_default or not self.default_provider:
            self.default_provider = alias
        print(f"[SynAI][LLM] Driver registrado: {alias}")

    # ─────────────────────────────────────────────────────────────────────────
    # REGISTRO DE FERRAMENTAS
    # ─────────────────────────────────────────────────────────────────────────
    def register_tool(self, name: str, func: Any):
        """Registra uma função Python como ferramenta executável."""
        self.tools[name] = func
        print(f"[SynAI][TOOL] Ferramenta registrada: {name}")

    def register_toolkit(self, toolkit: Dict[str, Any]):
        """Registra um dicionário inteiro de ferramentas de uma vez."""
        for name, func in toolkit.items():
            self.register_tool(name, func)

    # ─────────────────────────────────────────────────────────────────────────
    # EXECUÇÃO DE WORKFLOW DSL
    # ─────────────────────────────────────────────────────────────────────────
    async def execute_workflow(self, ast: Dict[str, Any], run_decl: Dict[str, Any], mock: bool = True) -> Dict[str, Any]:
        """Executa um workflow SynAI completo a partir do AST parseado."""
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

        data_flow: Dict[str, Any] = {}
        results = []
        print(f"🚀 Iniciando workflow '{wf_name}' [{orch_name}] (real={self.real})")

        for stmt in wf['statements']:
            stmt_type = stmt['type']

            # ── INTENT: execução de um agente ────────────────────────────────
            if stmt_type == 'Intent':
                agent_id = stmt['agent']
                agent_cfg = self._get_agent_config(orch, agent_id)
                if not agent_cfg:
                    print(f"⚠️  Agente '{agent_id}' não encontrado — pulando intent '{stmt['name']}'")
                    continue

                # Resolver input: prioridade fluxo > literal DSL > conexão prévia
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

                print(f"⚡ Intent: {stmt['name']} → agente '{agent_id}'")
                result = await self._dispatch_to_adapter(agent_cfg, stmt, input_data)

                data_flow[f"{agent_id}_output"] = result
                if stmt.get('output'):
                    data_flow[stmt['output']] = result

                results.append({'intent': stmt['name'], 'agent': agent_id, 'output': result})

            # ── CONNECT: ligação entre agentes ───────────────────────────────
            elif stmt_type == 'Connect':
                from_agent = stmt['from']
                to_agent = stmt['to']
                opts = stmt.get('options', {})
                from_data = data_flow.get(f"{from_agent}_output", 'N/A')
                data_flow[f"{to_agent}_input"] = from_data
                print(f"🔗 {from_agent}.output → {to_agent}.input  opts={opts}")

                if opts.get('async'):
                    await asyncio.sleep(0.05)
                if opts.get('timeout'):
                    await asyncio.sleep(min(0.1, opts['timeout'] / 100))

            else:
                print(f"⚠️ Instrução '{stmt_type}' desconhecida — ignorada.")

        print("✅ Workflow concluído.")
        return {'status': 'completed', 'results': results, 'flow': data_flow}

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS INTERNOS
    # ─────────────────────────────────────────────────────────────────────────
    def _get_agent_config(self, orch: Dict[str, Any], agent_id: str) -> Optional[Dict[str, Any]]:
        """Retorna a configuração de um agente pelo ID dentro do Orchestrator."""
        for block in orch.get('blocks', []):
            if block['type'] == 'AgentsBlock':
                for agent in block['agents']:
                    if agent['id'] == agent_id:
                        return agent
        return None

    def _resolve_input(self, raw_input: Any, data_flow: Dict[str, Any]) -> str:
        """Resolve referências de result('IntentName') para o valor real no flow."""
        if isinstance(raw_input, str) and raw_input.startswith("result(") and raw_input.endswith(")"):
            target = raw_input[7:-1].replace('"', '').replace("'", "")
            return data_flow.get(target, f"(resultado de {target} não encontrado)")
        return str(raw_input)

    async def _dispatch_to_adapter(self, agent_cfg: Dict[str, Any], intent: Dict[str, Any], input_data: str) -> str:
        """Encaminha execução ao adapter correto (LLM ou TOOL) com base no agent_type."""
        res_type = agent_cfg['properties'].get('agent_type', agent_cfg.get('agent_type', 'LLM'))
        agent_type = str(res_type).replace('"', '').upper()
        adapter = self.adapters.get(agent_type)
        if not adapter:
            print(f"⚠️  Adapter '{agent_type}' não implementado — mock.")
            return f"mock_result_{intent['name']}({input_data})"
        return await adapter(agent_cfg, intent, input_data)

    # ─────────────────────────────────────────────────────────────────────────
    # ADAPTER: TOOL
    # ─────────────────────────────────────────────────────────────────────────
    async def _tool_adapter(self, config: Dict[str, Any], intent: Dict[str, Any], input_data: str) -> str:
        """Adapter para execução de ferramentas Python registradas."""
        res_func = config.get('properties', {}).get('function', intent['name'])
        tool_name = str(res_func).replace('"', '')

        print(f"🛠️  Tool: {tool_name}({input_data[:60]}...)")

        if tool_name not in self.tools:
            msg = f"Aviso: Ferramenta '{tool_name}' não registrada no runtime."
            print(f"⚠️  [SynAI] {msg}")
            return msg

        try:
            func = self.tools[tool_name]
            if asyncio.iscoroutinefunction(func):
                result = await func(input_data)
            else:
                result = func(input_data)
            return str(result)
        except Exception as e:
            msg = f"Erro na ferramenta '{tool_name}': {e}"
            print(f"❌ [SynAI] {msg}")
            return msg

    # ─────────────────────────────────────────────────────────────────────────
    # ADAPTER: LLM
    # ─────────────────────────────────────────────────────────────────────────
    async def _llm_adapter(self, config: Dict[str, Any], intent: Dict[str, Any], input_data: str) -> str:
        """Adapter LLM — delega ao call_model com fallback automático."""
        model = config['properties'].get('model', 'unknown')
        preferred = config['properties'].get('provider', None)
        prompt = (
            f"Tarefa: {intent['name']}\n"
            f"Input: {input_data}\n"
            f"Formato de saída: {intent.get('output', 'texto')}."
        )
        return await self.call_model(model, prompt, preferred_provider=preferred)

    # ─────────────────────────────────────────────────────────────────────────
    # CALL MODEL — API Pública com Fallback Chain
    # ─────────────────────────────────────────────────────────────────────────
    async def call_model(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1024,
        endpoint: str = "",
        preferred_provider: Optional[str] = None,
    ) -> str:
        """
        Invoca um LLM diretamente, com fallback automático em cadeia.

        Ordem de tentativa:
            1. provider explícito (preferred_provider ou config do agente DSL)
            2. provider inferido pelo nome do modelo
            3. provider padrão (default_provider)
            4. toda a FALLBACK_CHAIN na ordem definida

        Args:
            model:              Slug do modelo (ex: 'deepseek-chat', 'gpt-4o').
            prompt:             Texto de entrada.
            max_tokens:         Limite de tokens na resposta.
            endpoint:           Endpoint customizado (legado, não recomendado).
            preferred_provider: Alias do provider preferencial.

        Returns:
            Resposta gerada pelo primeiro provider bem-sucedido.
        """
        print(f"[SynAI] call_model: '{model}'")

        # ── Detecção de perfil: 'best-coder', 'auto', etc. ──────────────────
        if is_profile(model):
            return await self._call_profile(model, prompt, max_tokens)

        self._dispatch_event("routing_start", {
            "model": model,
            "type": "single",
            "prompt": prompt[:150] + "..." if len(prompt) > 150 else prompt
        })

        # Resolver nome amigavel do registry para real slug
        registry_entry = resolve_model(model)
        if registry_entry:
            inferred, real_model = registry_entry
        else:
            inferred = _infer_provider(model)
            real_model = model

        # ── Option B: policy FREE sempre prevalece ──────────────────────────
        # Se o provider nativo do modelo e bloqueado pela policy, substitui
        # o slug pelo melhor modelo gratuito equivalente.
        if inferred and not self._is_allowed_by_policy(inferred):
            if self.policy in {"local", "sovereign"}:
                # Local: usa Ollama com llama3 como fallback soberano
                real_model = "llama3"
                inferred = "ollama"
                print(f"   [POLICY:{self.policy}] '{model}' bloqueado. Usando 'llama3' (ollama).")
            else:
                # Free/cheapest: substitui pelo melhor modelo OpenRouter :free
                real_model = RouterEngine.get_free_model("geral")
                inferred = "openrouter"
                print(f"   [POLICY:{self.policy}] '{model}' bloqueado. Usando '{real_model}' (openrouter:free).")
            self._dispatch_event("routing_policy_override", {
                "original_model": model,
                "policy": self.policy,
                "substituted_model": real_model,
                "substituted_provider": inferred,
            })

        # Montar lista de candidatos via RouterEngine (respeita a policy ativa)
        candidates = self._build_candidate_chain(preferred_provider, inferred)

        for alias in candidates:
            driver = self.llm_providers.get(alias)
            if not driver or (hasattr(driver, 'is_available') and not driver.is_available()):
                self._dispatch_event("routing_skip", {
                    "model": model,
                    "provider": alias,
                    "reason": "Driver not registered" if not driver else "Missing API key"
                })
                if driver:
                     print(f"   [SKIP] '{alias}' sem API key - pulando.")
                continue

            try:
                self._dispatch_event("routing_try", {
                    "model": model,
                    "provider": alias,
                    "slug": real_model
                })
                print(f"   >> Tentando '{alias}' (slug: '{real_model}')...")
                result = await driver.generate(prompt=prompt, model=real_model, max_tokens=max_tokens)
                self._dispatch_event("routing_success", {
                    "model": model,
                    "provider": alias,
                    "response": result[:150] + "..." if len(result) > 150 else result
                })
                print(f"   OK Resposta via '{alias}'.")
                return result
            except Exception as e:
                self._dispatch_event("routing_fail", {
                    "model": model,
                    "provider": alias,
                    "error": f"{type(e).__name__}: {e}"
                })
                print(f"   FAIL '{alias}' falhou: {type(e).__name__}: {e}. Proximo...")

        # Todos os providers falharam
        self._dispatch_event("routing_failed_all", {"model": model})
        if not self.real:
            return f"MOCK_RESPONSE({model}): {prompt[:40]}..."
        return f"Todos os providers falharam para o modelo '{model}'."

    # ─────────────────────────────────────────────────────────────────────────
    # CALL PROFILE — Roteamento por Perfil Semântico
    # ─────────────────────────────────────────────────────────────────────────
    async def _call_profile(
        self,
        profile: str,
        prompt: str,
        max_tokens: int = 1024,
    ) -> str:
        """
        Itera pelos modelos de um perfil (ex: 'best-coder') em ordem de prioridade,
        tentando cada um até obter resposta bem-sucedida.

        Para cada modelo da lista:
            1. Resolve o nome amigável → (provider_alias, api_slug) via MODEL_REGISTRY
            2. Se não estiver no registry, trata como slug direto e infere o provider
            3. Verifica se o driver está disponível (API key configurada)
            4. Tenta gerar; em falha, avança para o próximo
        """
        model_list = get_profile_models(profile)
        print(f"[SynAI][PROFILE] '{profile}' -> {len(model_list)} modelos candidatos (policy='{self.policy}')")

        self._dispatch_event("routing_start", {
            "model": profile,
            "type": "profile",
            "policy": self.policy,
            "prompt": prompt[:150] + "..." if len(prompt) > 150 else prompt
        })

        for friendly_name in model_list:
            # Resolver: nome amigavel ou slug direto
            registry_entry = resolve_model(friendly_name)
            if registry_entry:
                provider_alias, api_slug = registry_entry
            else:
                api_slug = friendly_name
                provider_alias = _infer_provider(friendly_name)

            if not provider_alias:
                self._dispatch_event("routing_skip", {
                    "model": profile,
                    "friendly_name": friendly_name,
                    "provider": "unknown",
                    "reason": "No provider inferred"
                })
                print(f"   [PROFILE] '{friendly_name}' sem provider inferido — pulando.")
                continue

            # ── Option B: policy FREE sempre prevalece ──────────────────────
            if not self._is_allowed_by_policy(provider_alias):
                self._dispatch_event("routing_skip", {
                    "model": profile,
                    "friendly_name": friendly_name,
                    "provider": provider_alias,
                    "reason": f"Blocked by policy '{self.policy}'"
                })
                print(f"   [PROFILE][POLICY:{self.policy}] '{friendly_name}' ({provider_alias}) bloqueado — pulando.")
                continue

            driver = self.llm_providers.get(provider_alias)
            if not driver:
                self._dispatch_event("routing_skip", {
                    "model": profile,
                    "friendly_name": friendly_name,
                    "provider": provider_alias,
                    "reason": "Driver not registered"
                })
                print(f"   [PROFILE] Provider '{provider_alias}' nao registrado — pulando '{friendly_name}'.")
                continue

            if hasattr(driver, 'is_available') and not driver.is_available():
                self._dispatch_event("routing_skip", {
                    "model": profile,
                    "friendly_name": friendly_name,
                    "provider": provider_alias,
                    "reason": "Missing API key"
                })
                print(f"   [PROFILE] '{provider_alias}' sem API key — pulando '{friendly_name}'.")
                continue

            try:
                self._dispatch_event("routing_try", {
                    "model": profile,
                    "friendly_name": friendly_name,
                    "provider": provider_alias,
                    "slug": api_slug
                })
                print(f"   [PROFILE] Tentando '{friendly_name}' via '{provider_alias}' (slug: {api_slug})...")
                result = await driver.generate(prompt=prompt, model=api_slug, max_tokens=max_tokens)
                self._dispatch_event("routing_success", {
                    "model": profile,
                    "friendly_name": friendly_name,
                    "provider": provider_alias,
                    "response": result[:150] + "..." if len(result) > 150 else result
                })
                print(f"   [PROFILE] OK via '{friendly_name}' ({provider_alias}).")
                return result
            except Exception as e:
                self._dispatch_event("routing_fail", {
                    "model": profile,
                    "friendly_name": friendly_name,
                    "provider": provider_alias,
                    "error": f"{type(e).__name__}: {e}"
                })
                print(f"   [PROFILE] '{friendly_name}' falhou: {type(e).__name__}: {e}. Proximo...")

        # Todos os modelos do perfil falharam
        self._dispatch_event("routing_failed_all", {"model": profile})
        if not self.real:
            return f"MOCK_PROFILE({profile}): {prompt[:40]}..."
        return f"Todos os modelos do perfil '{profile}' falharam."

    # ─────────────────────────────────────────────────────────────────────────
    # EMBEDDINGS — RAG Support
    # ─────────────────────────────────────────────────────────────────────────
    async def get_embedding(self, text: str, model: str = "models/gemini-embedding-001") -> Optional[list]:
        """
        Gera vetor de embedding via drivers disponíveis.
        Preferência: google → ollama → qualquer driver com get_embedding.
        """
        preferred_for_embed = ["google", "ollama"]

        for alias in preferred_for_embed:
            driver = self.llm_providers.get(alias)
            if driver and hasattr(driver, 'get_embedding'):
                try:
                    emb = await driver.get_embedding(text)
                    if emb:
                        return emb
                except Exception as e:
                    print(f"⚠️ Embedding via '{alias}' falhou: {e}")

        # Fallback: qualquer outro driver que suporte embeddings
        for alias, driver in self.llm_providers.items():
            if alias in preferred_for_embed:
                continue
            if hasattr(driver, 'get_embedding'):
                try:
                    emb = await driver.get_embedding(text)
                    if emb:
                        return emb
                except Exception:
                    continue

        print("❌ Nenhum driver de embedding encontrado.")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# EXECUÇÃO DIRETA (CLI / Debug)
# ─────────────────────────────────────────────────────────────────────────────
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
