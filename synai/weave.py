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
    """Compila/valida AST: schema + semântica (dependências)."""
    try:
        validate(instance=ast, schema=ast_schema)
        orchestrators = {}
        for decl in ast['declarations']:
            if decl['type'] == 'Orchestrator':
                name = decl['name']
                agents = {}
                for block in decl['blocks']:
                    if block['type'] == 'AgentsBlock':
                        for agent in block['agents']:
                            agents[agent['id']] = agent
                # Validação semântica: checa refs em workflows
                for block in decl['blocks']:
                    if block['type'] == 'Workflow':
                        for stmt in block['statements']:
                            if stmt['type'] == 'Intent':
                                if stmt['agent'] not in agents:
                                    raise ValueError(f"Agent '{stmt['agent']}' not defined in orchestrator '{name}'")
                            elif stmt['type'] == 'Connect':
                                if stmt['from'] not in agents or stmt['to'] not in agents:
                                    raise ValueError(f"Connect invalid in '{name}': {stmt['from']} -> {stmt['to']}")
                orchestrators[name] = {'agents': agents}
            elif decl['type'] == 'Run':
                orch_name = decl['orchestrator']
                if orch_name not in orchestrators:
                    raise ValueError(f"Run references undefined orchestrator '{orch_name}'")
        return ast  # AST validado/compilado
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(f"Schema validation error: {e.message}")
    except Exception as e:
        raise ValueError(f"Build error: {e}")
