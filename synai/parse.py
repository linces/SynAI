from lark import Lark, Transformer, Token, UnexpectedInput, Tree
import json
import uuid

grammar = r'''
start: program
program: declaration+
declaration: orchestrator_decl | run_decl

orchestrator_decl: "orchestrator" STRING "{" block+ "}"
block: agents_block | workflow_block
agents_block: "agents" "{" agent_entries "}"
agent_entries: agent_entry+
agent_entry: ID ":" AGENT_TYPE "{" properties "}"
properties: property*
property: ID ":" prop_value
prop_value: STRING | array
workflow_block: "workflow" STRING "{" statements "}"
statements: workflow_stmt+
workflow_stmt: start_stmt | step_stmt | connect_stmt | end_stmt
start_stmt: "start:" intent_stmt
step_stmt: "step:" intent_stmt
end_stmt: "end:" intent_stmt
intent_stmt: agent_id "." "intent" "(" arg_list ")"
arg_list: intent_name ("," input_arg)? ("," output_arg)?
intent_name: STRING
input_arg: "input:" STRING
output_arg: "output:" STRING
agent_id: ID
connect_stmt: "connect" from_agent "." "output" "->" to_agent "." "input" "{" options "}"
options: connect_opt*
from_agent: ID
to_agent: ID
connect_opt: async_opt | timeout_opt | transform_opt | retry_opt | filter_opt
async_opt: "async:" BOOL  # Changed to BOOL for "true" | "false"
timeout_opt: "timeout:" INT "s"
transform_opt: "transform:" STRING
retry_opt: "retry:" INT
filter_opt: "filter:" STRING
array: "[" strings "]"
strings: STRING ("," STRING)*
run_decl: "run" STRING "with" "workflow" STRING

AGENT_TYPE: /[A-Z][a-zA-Z0-9]+/
ID: /[a-zA-Z_][a-zA-Z0-9_]*/
STRING: /"[^"]*"/
INT: /[0-9]+/
BOOL: "true" | "false"  # New: for boolean options
COMMENT: /#.*/
%import common.WS
%ignore WS
%ignore COMMENT
'''

parser = Lark(grammar, start='program')

class SynTransformer(Transformer):
    def transform_children(self, children):
        if not children:
            return []
        transformed = []
        for c in children:
            if isinstance(c, (str, int, float, dict, list)):
                transformed.append(c)
            else:
                try:
                    transformed.append(self.transform(c))
                except Exception:
                    transformed.append(c)
        return [c for c in transformed if c is not None and not isinstance(c, Token)]

    def declaration(self, c): return self.transform_children(c)[0]
    def block(self, c): return self.transform_children(c)[0]
    def workflow_stmt(self, c): return self.transform_children(c)[0]
    def connect_opt(self, c): return self.transform_children(c)[0]

    def program(self, c):
        decls = self.transform_children(c)
        return {'type': 'Program', 'id': str(uuid.uuid4()), 'declarations': decls}

    def orchestrator_decl(self, c):
        n = self.transform_children(c)
        name = n[0]
        blocks = n[1:]
        return {'type': 'Orchestrator', 'id': str(uuid.uuid4()), 'name': name, 'blocks': blocks}

    def agents_block(self, c):
        agents = self.transform_children(c)[0]
        return {'type': 'AgentsBlock', 'id': str(uuid.uuid4()), 'agents': agents}

    def agent_entries(self, c): return self.transform_children(c)

    def agent_entry(self, c):
        n = self.transform_children(c)
        return {'type': 'Agent', 'id': n[0], 'agent_type': n[1], 'properties': n[2]}

    def properties(self, c):
        props = {}
        for child in self.transform_children(c):
            if isinstance(child, dict):
                props.update(child)
        return props

    def property(self, children):
        if not children:
            return {}
        n = []
        for ch in children:
            if isinstance(ch, (str, int, float, dict, list)):
                n.append(ch)
            else:
                try:
                    n.append(self.transform(ch))
                except Exception:
                    n.append(ch)
        key = n[0] if len(n) > 0 else "unknown"
        val = n[1] if len(n) > 1 else None
        return {key: val}

    def prop_value(self, children):
        if not children:
            return None
        first = children[0]
        if isinstance(first, (str, int, float, list, dict)):
            return first
        return self.transform(first)

    def workflow_block(self, c):
        n = self.transform_children(c)
        return {'type': 'Workflow', 'id': str(uuid.uuid4()), 'name': n[0], 'statements': n[1]}

    def statements(self, c): return self.transform_children(c)
    def start_stmt(self, c): return self.transform_children(c)[0]
    def step_stmt(self, c): return self.transform_children(c)[0]
    def end_stmt(self, c): return self.transform_children(c)[0]

    def intent_stmt(self, c):
        n = self.transform_children(c)
        agent = n[0]
        if isinstance(agent, Tree):
            agent = str(agent.children[0])
        args = n[1]
        return {'type': 'Intent', 'id': str(uuid.uuid4()), 'agent': agent,
                'name': args[0], 'input': args[1], 'output': args[2]}

    def arg_list(self, c):
        n = self.transform_children(c)
        name, input_, output_ = n[0], None, None
        for item in n[1:]:
            if isinstance(item, dict):
                input_ = item.get('input', input_)
                output_ = item.get('output', output_)
        return [name, input_, output_]

    def input_arg(self, c): return {'input': self.transform_children(c)[0]}
    def output_arg(self, c): return {'output': self.transform_children(c)[0]}

    def connect_stmt(self, c):
        n = self.transform_children(c)
        from_agent, to_agent = n[0], n[1]
        if isinstance(from_agent, Tree):
            from_agent = str(from_agent.children[0])
        if isinstance(to_agent, Tree):
            to_agent = str(to_agent.children[0])
        options = n[2] if len(n) > 2 else {}
        return {'type': 'Connect', 'id': str(uuid.uuid4()),
                'from': from_agent, 'to': to_agent, 'options': options}

    def options(self, c):
        opts = {}
        for child in self.transform_children(c):
            if isinstance(child, dict):
                opts.update(child)
        return opts

    def async_opt(self, c):
        n = self.transform_children(c)
        return {'async': n[0] == 'true'}  # Convert string to bool

    def timeout_opt(self, c):
        n = self.transform_children(c)
        return {'timeout': n[0]}

    def transform_opt(self, c):
        n = self.transform_children(c)
        return {'transform': n[0]}

    def retry_opt(self, c):
        n = self.transform_children(c)
        return {'retry': n[0]}

    def filter_opt(self, c):
        n = self.transform_children(c)
        return {'filter': n[0]}

    def run_decl(self, c):
        n = self.transform_children(c)
        return {'type': 'Run', 'id': str(uuid.uuid4()), 'orchestrator': n[0], 'workflow': n[1]}

    def array(self, children):
        if not children:
            return []
        first = children[0]
        if isinstance(first, list):
            return first
        if isinstance(first, (str, int)):
            return [first]
        return self.transform(first)

    def strings(self, children):
        result = []
        for ch in children:
            if isinstance(ch, str):
                result.append(ch)
            elif isinstance(ch, Tree):
                for sub in ch.children:
                    result.append(str(sub))
        return result

    def ID(self, s): return s.value
    def STRING(self, s): return s.value.strip('"')
    def INT(self, s): return int(s.value)
    def AGENT_TYPE(self, s): return s.value
    def BOOL(self, s): return s.value == 'true'  # Convert to bool

# --- SANITIZAÇÃO FINAL
def sanitize_tree(obj):
    """Remove objetos Tree/Token e converte recursivamente."""
    if isinstance(obj, Tree):
        return sanitize_tree(obj.children[0]) if obj.children else None
    if isinstance(obj, Token):
        return str(obj.value)
    if isinstance(obj, dict):
        return {sanitize_tree(k): sanitize_tree(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_tree(x) for x in obj]
    if isinstance(obj, (str, int, float)) or obj is None:
        return obj
    return str(obj)


def parse_synai(code: str) -> dict:
    try:
        tree = parser.parse(code)
        transformer = SynTransformer()
        ast = transformer.transform(tree)
        return sanitize_tree(ast)
    except UnexpectedInput as e:
        raise ValueError(f"Erro de parsing na linha {e.line}, coluna {e.column}: {e.get_context(code)}")
    except Exception as e:
        raise ValueError(f"Parse error: {e}")