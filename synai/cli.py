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
    output = synx_path.replace('.synx', '_linked.synx')
    result = weave_linker(ast, output)
    click.echo(result)

    if diagram:
        import matplotlib.pyplot as plt
        G = nx.node_link_graph(json.load(open(output))['graph'])
        nx.draw(G, with_labels=True, node_color='lightblue', node_size=1800, font_size=8)
        plt.show()

@cli.command()
@click.argument('synx_path')
def run(synx_path):
    # Auto-detect linked file if not provided
    if not synx_path.endswith('_linked.synx'):
        linked_path = synx_path.replace('.synx', '_linked.synx')
        if os.path.exists(linked_path):
            synx_path = linked_path
            click.echo(f"Usando arquivo linked: {synx_path}")
        else:
            click.echo(f"Erro: {synx_path} não encontrado. Rode 'synai link' antes.")
            return

    if not os.path.exists(synx_path):
        click.echo(f"Erro: {synx_path} não encontrado.")
        return

    data = json.load(open(synx_path))
    G = nx.node_link_graph(data['graph'])
    click.echo(f"Executando {synx_path}...")
    for node in nx.topological_sort(G):
        nd = G.nodes[node]
        if nd.get('type') == 'intent':
            click.echo(f"🎯 Intent {nd['agent']}.{nd['name']} (in={nd.get('input')}, out={nd.get('output')})")
    click.echo("Execução simulada concluída.")

if __name__ == '__main__':
    cli()