from lark import Lark, Transformer, Token
import json

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
workflow_stmt: start_stmt | connect_stmt | end_stmt
start_stmt: "start:" intent_stmt
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
connect_opt: async_opt | timeout_opt
async_opt: "async:" "true"
timeout_opt: "timeout:" INT "s"
array: "[" strings "]"
strings: STRING ("," STRING)*
run_decl: "run" STRING "with" "workflow" STRING

AGENT_TYPE: /[A-Z][a-zA-Z0-9]+/
ID: /[a-zA-Z_][a-zA-Z0-9_]*/
STRING: /"[^"]*"/
INT: /[0-9]+/

%import common.WS
%ignore WS
'''

parser = Lark(grammar, start='program')

class SynTransformer(Transformer):
    def transform_children(self, children):
        transformed = [self.transform(c) for c in children]
        return [c for c in transformed if c is not None]

    # Punctuation to None
    def COMMA(self, s):
        return None

    def COLON(self, s):
        return None

    def LBRACE(self, s):
        return None

    def RBRACE(self, s):
        return None

    def LPAREN(self, s):
        return None

    def RPAREN(self, s):
        return None

    def ARROW(self, s):
        return None  # for ->

    def DOT(self, s):
        return None

    def program(self, children):
        return {'type': 'Program', 'declarations': self.transform_children(children)}

    def orchestrator_decl(self, children):
        non_punct = [c for c in self.transform_children(children) if c is not None]
        name = non_punct[0]
        blocks = non_punct[1:]
        return {'type': 'Orchestrator', 'name': name, 'blocks': blocks}

    def agents_block(self, children):
        agent_entries = self.transform_children(children)[0]
        return {'type': 'AgentsBlock', 'agents': agent_entries}

    def agent_entries(self, children):
        return self.transform_children(children)

    def agent_entry(self, children):
        non_punct = [c for c in self.transform_children(children) if c is not None]
        id_ = non_punct[0]
        agent_type = non_punct[1]
        properties = non_punct[2]
        return {'type': 'Agent', 'id': id_, 'agent_type': agent_type, 'properties': properties}

    def properties(self, children):
        props = {}
        for child in self.transform_children(children):
            if isinstance(child, dict):
                props.update(child)
        return props

    def property(self, children):
        non_punct = [c for c in self.transform_children(children) if c is not None and not isinstance(c, Token)]
        key = non_punct[0]
        value = non_punct[1]
        if key == 'capabilities':
            return {'capabilities': value}
        else:
            return {key: value}

    def prop_value(self, children):
        return self.transform_children(children)[0]

    def workflow_block(self, children):
        non_punct = [c for c in self.transform_children(children) if c is not None]
        name = non_punct[0]
        statements = non_punct[1]
        return {'type': 'Workflow', 'name': name, 'statements': statements}

    def statements(self, children):
        return self.transform_children(children)

    def workflow_stmt(self, children):
        return self.transform_children(children)[0]

    def start_stmt(self, children):
        return self.transform_children(children)[0]

    def end_stmt(self, children):
        return self.transform_children(children)[0]

    def intent_stmt(self, children):
        non_punct = [c for c in self.transform_children(children) if c is not None]
        agent = non_punct[0]
        arg_list = non_punct[1]
        name = arg_list[0]
        input_ = arg_list[1] if len(arg_list) > 1 else None
        output = arg_list[2] if len(arg_list) > 2 else None
        return {'type': 'Intent', 'agent': agent, 'name': name, 'input': input_, 'output': output}

    def arg_list(self, children):
        non_punct = [c for c in self.transform_children(children) if c is not None and not isinstance(c, Token)]
        name = non_punct[0]
        input_ = None
        output = None
        if len(non_punct) > 1:
            if isinstance(non_punct[1], dict) and 'input' in non_punct[1]:
                input_ = non_punct[1]['input']
            else:
                output = non_punct[1]['output'] if isinstance(non_punct[1], dict) else non_punct[1]
        if len(non_punct) > 2:
            output = non_punct[2]['output'] if isinstance(non_punct[2], dict) else non_punct[2]
        return [name, input_, output]

    def input_arg(self, children):
        non_punct = [c for c in self.transform_children(children) if c is not None and not isinstance(c, Token)]
        return {'input': non_punct[0]}

    def output_arg(self, children):
        non_punct = [c for c in self.transform_children(children) if c is not None and not isinstance(c, Token)]
        return {'output': non_punct[0]}

    def connect_stmt(self, children):
        non_punct = [c for c in self.transform_children(children) if c is not None and not isinstance(c, Token)]
        from_ = non_punct[0]
        to_ = non_punct[1]
        options = non_punct[2]
        return {'type': 'Connect', 'from': from_, 'to': to_, 'options': options}

    def options(self, children):
        opts = {}
        for child in self.transform_children(children):
            if isinstance(child, dict):
                opts.update(child)
        return opts

    def connect_opt(self, children):
        return self.transform_children(children)[0]

    def async_opt(self, children):
        return {'async': True}

    def timeout_opt(self, children):
        non_punct = [c for c in self.transform_children(children) if c is not None and not isinstance(c, Token)]
        return {'timeout': non_punct[0]}

    def run_decl(self, children):
        non_punct = [c for c in self.transform_children(children) if c is not None and not isinstance(c, Token)]
        orch = non_punct[0]
        wf = non_punct[1]
        return {'type': 'Run', 'orchestrator': orch, 'workflow': wf}

    def array(self, children):
        non_punct = [c for c in self.transform_children(children) if c is not None and not isinstance(c, Token)]
        return non_punct[0]

    def strings(self, children):
        str_list = [c for c in self.transform_children(children) if isinstance(c, str)]
        return str_list

    def ID(self, s):
        return s.value

    def STRING(self, s):
        return s.value.strip('"')

    def INT(self, s):
        return int(s.value)

    def AGENT_TYPE(self, s):
        return s.value

def parse_synai(code: str) -> dict:
    try:
        tree = parser.parse(code)
        transformer = SynTransformer()
        ast = transformer.transform(tree)
        return ast
    except Exception as e:
        raise ValueError(f"Parse error: {e}")

if __name__ == '__main__':
    demo_code = '''orchestrator "demo" {
  agents {
    grok: LLM { model: "grok-4" capabilities: ["reason", "code"] }
  }
  workflow "simple" {
    start: grok.intent("analyze", input: "data.txt")
    connect grok.output -> grok.input { async: true timeout: 30s }
    end: grok.intent("summarize", output: "result.txt")
  }
}
run "demo" with workflow "simple"'''

    try:
        ast = parse_synai(demo_code)
        print(json.dumps(ast, indent=2))
    except Exception as e:
        print(f"Error: {e}")