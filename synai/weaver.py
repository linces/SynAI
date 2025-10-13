import networkx as nx
import json
from .weave import build_synai

def weave_linker(ast: dict, output_path: str = None) -> dict:
    """Linker: Gera grafo de roteamento e bytecode .synx."""
    validated_ast = build_synai(ast)
    G = nx.DiGraph()
    
    # Extrai e adiciona agents como nodes
    for decl in validated_ast['declarations']:
        if decl['type'] == 'Orchestrator':
            for block in decl['blocks']:
                if block['type'] == 'AgentsBlock':
                    for agent in block['agents']:
                        G.add_node(agent['id'], type='agent', **agent['properties'])
                if block['type'] == 'Workflow':
                    # Adiciona intents como nodes
                    for stmt in block['statements']:
                        if stmt['type'] == 'Intent':
                            node_id = f"{stmt['agent']}_{stmt['name']}"
                            G.add_node(node_id, type='intent', agent=stmt['agent'], name=stmt['name'], 
                                     input=stmt.get('input'), output=stmt.get('output'))
                        elif stmt['type'] == 'Connect':
                            # Adiciona edges para connects
                            from_node = f"{stmt['from']}_output"
                            to_node = f"{stmt['to']}_input"
                            G.add_edge(from_node, to_node, **stmt['options'])
    
    # Bytecode: grafo + AST
    bytecode = {
        'graph': nx.node_link_data(G),
        'validated_ast': validated_ast,
        'nodes_count': G.number_of_nodes(),
        'edges_count': G.number_of_edges()
    }
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(bytecode, f, indent=2, default=str)
        return f"Linked: {output_path} (grafo: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges)"
    return bytecode

# Exemplo de uso
if __name__ == '__main__':
    from .parse import parse_synai
    with open('../examples/demo.synai', 'r') as f:
        code = f.read()
    ast = parse_synai(code)
    result = weave_linker(ast, 'demo_linked.synx')
    print(result)
