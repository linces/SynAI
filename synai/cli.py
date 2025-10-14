import click
import os
import json
import networkx as nx
from .parse import parse_synai
from .weave import build_synai
from .weaver import weave_linker

@click.group()
def cli():
    """SynAI CLI - Orquestre IAs com DSL declarativa."""

@cli.command()
@click.argument('file_path')
@click.option('-o', '--output', default=None)
@click.option('--verbose', is_flag=True)
def parse(file_path, output, verbose):
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    ast = parse_synai(code)
    if verbose:
        click.echo(json.dumps(ast, indent=2))
    if output:
        os.makedirs(os.path.dirname(output) or '.', exist_ok=True)
        with open(output, 'w', encoding='utf-8') as of:
            json.dump(ast, of, indent=2)
        click.echo(f"AST salva em {output}")
    else:
        click.echo("AST gerada com sucesso.")

@cli.command()
@click.argument('file_path')
@click.option('-o', '--output', default=None)
@click.option('--verbose', is_flag=True)
def build(file_path, output, verbose):
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    ast = parse_synai(code)
    validated = build_synai(ast)
    if verbose:
        click.echo(json.dumps(validated, indent=2))
    if validated.get('warnings'):
        click.echo("Avisos:")
        for w in validated['warnings']:
            click.echo(f" ⚠️  {w}")
    if output:
        os.makedirs(os.path.dirname(output) or '.', exist_ok=True)
        with open(output, 'w', encoding='utf-8') as of:
            json.dump(validated, of, indent=2)
        click.echo(f"AST validada salva em {output}")

@cli.command()
@click.argument('synx_path')
@click.option('--diagram', is_flag=True)
def link(synx_path, diagram):
    with open(synx_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    ast = data.get('validated_ast', data)
    # Fix path: keep same dir, no double replace (handled in weaver)
    result = weave_linker(ast, synx_path)
    click.echo(result)

    if diagram:
        import matplotlib.pyplot as plt
        # Get the actual output from result
        if '_linked' in result:
            output = result.split('Linked: ')[1].split(' (')[0]
        else:
            output = synx_path.replace('.synx', '_linked.synx')
        G = nx.node_link_graph(json.load(open(output))['graph'])
        nx.draw(G, with_labels=True, node_color='lightblue', node_size=1800, font_size=8)
        plt.show()

@cli.command()
@click.argument('synx_path')
def run(synx_path):
    # Auto-detect linked file with path fix (no double)
    dir_name = os.path.dirname(synx_path)
    base_name = os.path.basename(synx_path)
    if '_linked' not in base_name:
        linked_base = base_name.replace('.synx', '_linked.synx')
        linked_path = os.path.join(dir_name, linked_base)
        if os.path.exists(linked_path):
            synx_path = linked_path
            click.echo(f"Usando arquivo linked: {synx_path}")
        else:
            click.echo(f"Erro: {synx_path} não encontrado. Rode 'synai link' antes.")
            return
    # If already _linked, use as is

    if not os.path.exists(synx_path):
        click.echo(f"Erro: {synx_path} não encontrado.")
        return

    data = json.load(open(synx_path, 'r', encoding='utf-8'))
    ast = data['validated_ast']
    G = nx.node_link_graph(data['graph'])

    # Find run and workflow
    run_decl = next((d for d in ast['declarations'] if d['type'] == 'Run'), None)
    if not run_decl:
        click.echo("Erro: No 'run' declaration in AST.")
        return
    orch_name = run_decl['orchestrator']
    wf_name = run_decl['workflow']

    orch = next((d for d in ast['declarations'] if d['type'] == 'Orchestrator' and d['name'] == orch_name), None)
    if not orch:
        click.echo(f"Erro: Orchestrator '{orch_name}' not found.")
        return

    wf = next((b for b in orch['blocks'] if b['type'] == 'Workflow' and b['name'] == wf_name), None)
    if not wf:
        click.echo(f"Erro: Workflow '{wf_name}' not found.")
        return

    click.echo(f"Executando workflow '{wf_name}' de '{orch_name}'...")
    data_flow = {}  # Simulate data: key = output port, value = data
    for stmt in wf['statements']:
        if stmt['type'] == 'Intent':
            input_data = data_flow.get(f"{stmt['agent']}_input", stmt.get('input', 'N/A'))
            click.echo(f"🎯 Executando intent {stmt['agent']}.{stmt['name']} (input: {input_data})")
            # Mock output
            output_data = f"result_{stmt['name']}"
            data_flow[f"{stmt['agent']}_output"] = output_data
            click.echo(f"   Output: {output_data}")
        elif stmt['type'] == 'Connect':
            from_data = data_flow.get(f"{stmt['from']}_output", 'N/A')
            data_flow[f"{stmt['to']}_input"] = from_data
            click.echo(f"🔗 Conectando {stmt['from']}.output -> {stmt['to']}.input (data: {from_data}, options: {stmt['options']})")

    click.echo("Execução simulada concluída.")

if __name__ == '__main__':
    cli()