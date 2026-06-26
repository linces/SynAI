import json
import os
import uuid
import networkx as nx
from datetime import datetime
from typing import Dict, Any
from networkx.readwrite import json_graph

def weave_linker(ast: Dict[str, Any], source_path: str) -> str:
    """
    Constrói e salva o arquivo linked (.synx_linked).
    Transforma o AST validado em grafo executável (com suporte a SynRuntime).
    """

    if not ast or 'declarations' not in ast:
        raise ValueError("AST inválida ou vazia para o linker.")

    orchestrators = [d for d in ast['declarations'] if d['type'] == 'Orchestrator']
    runs = [d for d in ast['declarations'] if d['type'] == 'Run']

    if not orchestrators:
        raise ValueError("Nenhum Orchestrator encontrado no AST.")
    if not runs:
        raise ValueError("Nenhum bloco 'Run' encontrado no AST.")

    print("🧵 Iniciando linkagem do AST...")

    G = nx.DiGraph()
    node_count = 0
    edge_count = 0

    # Constrói nós (agentes) e conexões (edges)
    for orch in orchestrators:
        orch_name = orch.get('name', 'unnamed_orchestrator')
        print(f"🔧 Orchestrator detectado: {orch_name}")
        agents_by_id = {}

        for block in orch.get('blocks', []):
            if block['type'] == 'AgentsBlock':
                for agent in block.get('agents', []):
                    agent_id = agent['id']
                    G.add_node(agent_id, **agent['properties'], type=agent['agent_type'], orchestrator=orch_name)
                    agents_by_id[agent_id] = agent
                    node_count += 1
                    print(f"🧠  Agente adicionado: {agent_id} ({agent['agent_type']})")

        # Fluxos de workflow
        for block in orch.get('blocks', []):
            if block['type'] == 'Workflow':
                wf_name = block.get('name', 'unnamed_workflow')
                print(f"🔄  Workflow: {wf_name}")
                for stmt in block.get('statements', []):
                    if stmt['type'] == 'Connect':
                        src = stmt['from']
                        dst = stmt['to']
                        options = stmt.get('options', {})
                        if src in agents_by_id and dst in agents_by_id:
                            G.add_edge(src, dst, **options)
                            edge_count += 1
                            print(f"🔗  Conexão: {src} → {dst} ({options})")
                        else:
                            print(f"⚠️  Conexão ignorada (agente não encontrado): {src} -> {dst}")

    # Metadados
    metadata = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "source": os.path.basename(source_path),
        "nodes": node_count,
        "edges": edge_count,
        "version": "1.0.0"
    }

    # Estrutura final
    linked_data = {
        "validated_ast": ast,
        "graph": json_graph.node_link_data(G),
        "metadata": metadata
    }

    # Caminho de saída: mantém o diretório original e altera o nome do arquivo com robustez
    dir_name = os.path.dirname(source_path)
    base_name = os.path.basename(source_path)
    if base_name.endswith('.synx'):
        linked_base = base_name[:-5] + '_linked.synx'
    else:
        root, ext = os.path.splitext(base_name)
        linked_base = f"{root}_linked{ext}"
    output_path = os.path.join(dir_name, linked_base)
    os.makedirs(dir_name or '.', exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(linked_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Linkagem concluída: {output_path}")
    print(f"📊 Nós: {node_count} | Arestas: {edge_count}")
    return f"Linked: {output_path} ({node_count} nós, {edge_count} conexões)"

# ------------------------------------------------------------------------
# EXECUÇÃO DIRETA DE TESTE
# ------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Uso: python weaver.py <arquivo.synx>")
        exit(1)
    src = sys.argv[1]
    if not os.path.exists(src):
        print(f"Arquivo não encontrado: {src}")
        exit(1)

    with open(src, 'r', encoding='utf-8') as f:
        ast = json.load(f)
    result = weave_linker(ast, src)
    print(result)
