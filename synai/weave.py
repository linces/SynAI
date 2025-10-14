import jsonschema
from jsonschema import validate

ast_schema = {
    "type": "object",
    "properties": {
        "type": {"const": "Program"},
        "declarations": {"type": "array", "minItems": 1}
    },
    "required": ["type", "declarations"]
}

def build_synai(ast: dict) -> dict:
    """Valida e enriquece AST."""
    warnings = []
    try:
        validate(instance=ast, schema=ast_schema)
        orchestrators = {}

        for decl in ast['declarations']:
            if decl['type'] == 'Orchestrator':
                name = decl.get('name', '')
                agents = {a['id']: a for block in decl.get('blocks', []) if block['type'] == 'AgentsBlock' for a in block.get('agents', [])}

                # valida intents e conexões
                for block in decl.get('blocks', []):
                    if block['type'] == 'Workflow':
                        for stmt in block.get('statements', []):
                            if stmt['type'] == 'Intent' and stmt['agent'] not in agents:
                                raise ValueError(f"Agent '{stmt['agent']}' not definido em '{name}'")
                            elif stmt['type'] == 'Connect':
                                if stmt['from'] not in agents or stmt['to'] not in agents:
                                    raise ValueError(f"Conexão inválida '{stmt['from']} -> {stmt['to']}'")
                if not agents:
                    warnings.append(f"Atenção: Orchestrator '{name}' sem agentes.")
                orchestrators[name] = {'agents': agents}

            elif decl['type'] == 'Run':
                if decl['orchestrator'] not in orchestrators:
                    warnings.append(f"Run refere-se a orchestrator indefinido '{decl['orchestrator']}'.")

        ast['warnings'] = warnings
        return ast
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(f"Schema inválido: {e.message}")
    except Exception as e:
        raise ValueError(f"Erro no build: {e}")
