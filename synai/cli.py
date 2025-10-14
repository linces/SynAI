import click
import os
import json
import networkx as nx
from .parse import parse_synai
from .weave import build_synai
from .weaver import weave_linker

@click.group()
def cli():
    """SynAI CLI: Orquestre IAs com DSL declarativa."""

@cli.command()
@click.argument('file_path')
@click.option('-o', '--output', default=None, help='Output .synx file')
def parse(file_path, output):
    """Parse DSL file to AST."""

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    ast = parse_synai(code)
    click.echo(f"AST parsed: {ast['type']}")
    if output:
        os.makedirs(os.path.dirname(output) or '.', exist_ok=True)
        with open(output, 'w', encoding='utf-8') as of:
            json.dump(ast, of, indent=2)
        click.echo(f"AST saved to {output}")

@cli.command()
@click.argument('file_path')
@click.option('-o', '--output', default=None, help='Output .synx file')
def build(file_path, output):
    """Build DSL to validated AST."""

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    ast = parse_synai(code)
    validated = build_synai(ast)
    click.echo("Build successful")
    if output:
        os.makedirs(os.path.dirname(output) or '.', exist_ok=True)
        with open(output, 'w', encoding='utf-8') as of:
            json.dump(validated, of, indent=2)
        click.echo(f"Built to {output}")

@cli.command()
@click.argument('synx_path')
def link(synx_path):
    """Link bytecode to runtime graph."""

    with open(synx_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    ast = data.get('validated_ast', data)  # Fallback para AST direto
    output = synx_path.replace('.synx', '_linked.synx')
    os.makedirs(os.path.dirname(output) or '.', exist_ok=True)
    result = weave_linker(ast, output)
    click.echo(result)

@cli.command()
@click.argument('synx_path')
def run(synx_path):
    """Run linked workflow (simulated execution)."""

    if not os.path.exists(synx_path):
        click.echo(f"Error: {synx_path} not found. Run 'synai link' first.")
        return

    click.echo(f"Running execution of {synx_path}...")
    try:
        with open(synx_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'graph' not in data:
            click.echo("Error: No graph in bytecode. Run 'synai link' first.")
            return
        G = nx.node_link_graph(data['graph'])
        # Simulate topological execution
        topo_order = list(nx.topological_sort(G))
        for node in topo_order:
            node_data = G.nodes.get(node, {})
            if node_data.get('type') == 'intent':
                input_val = node_data.get('input', 'N/A')
                output_val = node_data.get('output', 'N/A')
                click.echo(f"Executing intent: {node_data.get('agent', 'unknown')}.{node_data.get('name', 'unknown')} (input: {input_val}, output: {output_val})")
        # Print connections
        for edge in G.edges(data=True):
            click.echo(f"Connecting {edge[0]} -> {edge[1]} with options: {edge[2]}")
        click.echo("Workflow completed successfully.")
    except Exception as e:
        click.echo(f"Execution error: {e}")

if __name__ == '__main__':
    cli()