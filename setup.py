from setuptools import setup, find_packages

setup(
    name="synai",
    version="1.4",
    packages=find_packages(),
    install_requires=["lark", "click", "networkx", "jsonschema"],
    entry_points={"console_scripts": ["synai=synai.cli:cli"]},
    description="SynAI: Cognitive Mesh Language for AI Orchestration",
    author="Linces Marques",
    author_email="linces@gmail.com",
)
