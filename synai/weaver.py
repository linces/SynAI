import networkx as nx
import json
import os
from .weave import build_synai

def weave_linker(ast: dict, output_path: str = None) -> dict:
    """Gera grafo de roteamento e bytecode .synx."""
    validated_ast = build_synai(ast)
    G = nx.DiGraph()

    for decl in validated_ast['declarations']:
        if decl['type'] == 'Orchestrator':
            for block in decl['blocks']:
                if block['type'] == 'AgentsBlock':
                    for agent in block['agents']:
                        G.add_node(f"agent:{agent['id']}", type='agent', **agent['properties'])
                elif block['type'] == 'Workflow':
                    for stmt in block['statements']:
                        if stmt['type'] == 'Intent':
                            node_id = f"intent:{stmt['agent']}:{stmt['name']}"
                            G.add_node(node_id, type='intent', agent=stmt['agent'],
                                       name=stmt['name'], input=stmt.get('input'),
                                       output=stmt.get('output'))
                        elif stmt['type'] == 'Connect':
                            from_node = f"agent:{stmt['from']}"
                            to_node = f"agent:{stmt['to']}"
                            G.add_edge(from_node, to_node, **stmt['options'])

    bytecode = {
        'graph': nx.node_link_data(G),
        'validated_ast': validated_ast,
        'nodes_count': G.number_of_nodes(),
        'edges_count': G.number_of_edges()
    }
    if output_path:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(bytecode, f, indent=2, default=str)
        return f"Linked: {output_path} ({G.number_of_nodes()} nós, {G.number_of_edges()} conexões)"
    return bytecode
