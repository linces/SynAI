import click
import os
import json
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
    """Run linked workflow (mock)."""

    click.echo(f"Running mock execution of {synx_path}...")
    click.echo("Output: Workflow completed successfully (mock).")

if __name__ == '__main__':
    cli()