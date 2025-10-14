import asyncio
from typing import Dict, Any
import anthropic
import openai
import os
from dotenv import load_dotenv  # Auto-load .env

load_dotenv()  # Carrega .env automaticamente

class SynRuntime:
    def __init__(self, api_key: str = None, xai_key: str = None):
        # Anthropic (Claude)
        anthro_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if anthro_key:
            self.client_anthro = anthropic.Anthropic(api_key=anthro_key)
        else:
            self.client_anthro = None

        # xAI (Grok)
        xai_key = xai_key or os.getenv('XAI_API_KEY')
        if xai_key:
            self.client_grok = openai.OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1")
        else:
            self.client_grok = None

        self.adapters = {
            'LLM': self._llm_adapter,
            # Expanda para 'Vision', 'Tool', etc.
        }

    async def execute_workflow(self, ast: Dict[str, Any], run_decl: Dict[str, Any], mock: bool = True) -> Dict[str, Any]:
        """Executa workflow async, mapeando intents para adapters."""
        orch_name = run_decl['orchestrator']
        wf_name = run_decl['workflow']
        orch = next((d for d in ast['declarations'] if d['type'] == 'Orchestrator' and d['name'] == orch_name), None)
        wf = next((b for b in orch['blocks'] if b['type'] == 'Workflow' and b['name'] == wf_name), None)

        data_flow = {}  # Input/output simulation
        results = []

        for stmt in wf['statements']:
            if stmt['type'] == 'Intent':
                agent = stmt['agent']
                agent_config = next((a for block in orch['blocks'] if block['type'] == 'AgentsBlock' for a in block['agents'] if a['id'] == agent), None)
                adapter = self.adapters.get(agent_config['agent_type'])
                input_data = data_flow.get(f"{agent}_input", stmt.get('input', ''))
                if mock:
                    output = f"mock_result_{stmt['name']}({input_data})"
                else:
                    output = await adapter(agent_config, stmt, input_data)
                data_flow[f"{agent}_output"] = output
                results.append({'intent': stmt['name'], 'output': output})
            elif stmt['type'] == 'Connect':
                from_data = data_flow.get(f"{stmt['from']}_output", 'N/A')
                data_flow[f"{stmt['to']}_input"] = from_data
                # Apply options (async/retry in real)
                if stmt['options'].get('async'):
                    await asyncio.sleep(0.1)

        return {'status': 'completed', 'results': results}

    async def _llm_adapter(self, config: Dict[str, Any], intent: Dict[str, Any], input_data: str) -> str:
        """Adapter para LLM (Anthropic ou xAI baseado no model)."""
        model = config['properties']['model']
        prompt = f"Execute {intent['name']} com input: {input_data}. Output format: {intent.get('output', 'text')}."
        
        if 'grok' in model.lower() and self.client_grok:
            # xAI Grok
            try:
                response = self.client_grok.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024
                )
                return response.choices[0].message.content or "No response"
            except openai.APIError as e:
                print(f"Erro na xAI API: {e}. Usando fallback mock.")
                return f"grok_mock_{intent['name']} (erro: {e})"
        elif self.client_anthro:
            # Anthropic Claude
            try:
                message = self.client_anthro.messages.create(
                    model=model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}]
                )
                return message.content[0].text if message.content else "No response"
            except anthropic.BadRequestError as e:
                if "credit balance is too low" in str(e):
                    print("Créditos baixos — vá ao console para adicionar: https://console.anthropic.com/settings/plans")
                    return f"claude_mock_{intent['name']} (créditos insuficientes)"
                else:
                    raise ValueError(f"Erro na API: {e}")
            except Exception as e:
                print(f"Erro inesperado na API: {e}. Usando fallback mock.")
                return f"claude_mock_{intent['name']} (erro: {e})"
        else:
            print("Nenhuma API configurada para LLM. Usando mock.")
            return f"mock_{intent['name']} (no API)"

# Exemplo de uso
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
        runtime = SynRuntime()
        result = asyncio.run(runtime.execute_workflow(data['validated_ast'], data['validated_ast']['declarations'][-1], mock=False))
        print(json.dumps(result, indent=2))