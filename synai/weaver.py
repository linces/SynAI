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
                        agent_id = agent['id']
                        G.add_node(f"{agent_id}_input", type='port', agent=agent_id, port='input')
                        G.add_node(f"{agent_id}_output", type='port', agent=agent_id, port='output')
                        G.add_node(f"agent:{agent_id}", type='agent', **agent['properties'])
                        # Edges internas do agent: input -> agent -> output
                        G.add_edge(f"{agent_id}_input", f"agent:{agent_id}")
                        G.add_edge(f"agent:{agent_id}", f"{agent_id}_output")
                elif block['type'] == 'Workflow':
                    for stmt in block['statements']:
                        if stmt['type'] == 'Intent':
                            intent_id = f"intent:{stmt['agent']}:{stmt['name']}"
                            G.add_node(intent_id, type='intent', agent=stmt['agent'], name=stmt['name'], 
                                       input=stmt.get('input'), output=stmt.get('output'))
                            # Connect intent to agent ports
                            G.add_edge(f"{stmt['agent']}_input", intent_id)
                            G.add_edge(intent_id, f"{stmt['agent']}_output")
                        elif stmt['type'] == 'Connect':
                            from_port = f"{stmt['from']}_output"
                            to_port = f"{stmt['to']}_input"
                            G.add_edge(from_port, to_port, **stmt['options'])

    # Check for cycles
    if not nx.is_directed_acyclic_graph(G):
        print("Warning: Graph has cycles; run will use sequential execution.")

    bytecode = {
        'graph': nx.node_link_data(G),
        'validated_ast': validated_ast,
        'nodes_count': G.number_of_nodes(),
        'edges_count': G.number_of_edges()
    }
    if output_path:
        # Fix path: keep same dir, no double replace
        dir_name = os.path.dirname(output_path)
        base_name = os.path.basename(output_path)
        if '_linked' in base_name:
            full_output = output_path  # Already linked, overwrite
        else:
            linked_base = base_name.replace('.synx', '_linked.synx')
            full_output = os.path.join(dir_name, linked_base)
        os.makedirs(dir_name, exist_ok=True)
        with open(full_output, 'w', encoding='utf-8') as f:
            json.dump(bytecode, f, indent=2, default=str)
        return f"Linked: {full_output} ({G.number_of_nodes()} nós, {G.number_of_edges()} conexões)"
    return bytecode