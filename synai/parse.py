from lark import Lark, Transformer
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
        return [self.transform(c) for c in children]

    def program(self, children):
        return {'type': 'Program', 'declarations': self.transform_children(children)}

    def orchestrator_decl(self, children):
        name = children[0]
        blocks = self.transform_children(children[1:])
        return {'type': 'Orchestrator', 'name': name, 'blocks': blocks}

    def agents_block(self, children):
        agent_entries = self.transform(children[0])
        return {'type': 'AgentsBlock', 'agents': agent_entries}

    def agent_entries(self, children):
        return self.transform_children(children)

    def agent_entry(self, children):
        id_ = children[0]
        agent_type = children[1]
        properties = children[2]
        return {'type': 'Agent', 'id': id_, 'agent_type': agent_type, 'properties': properties}

    def properties(self, children):
        props = {}
        for child in children:
            prop_dict = self.transform(child)
            props.update(prop_dict)
        return props

    def property(self, children):
        key = children[0]
        value = children[1]
        if key == 'capabilities':
            return {'capabilities': value}
        else:
            return {key: value}

    def prop_value(self, children):
        return self.transform(children[0])

    def workflow_block(self, children):
        name = children[0]
        statements = self.transform(children[1])
        return {'type': 'Workflow', 'name': name, 'statements': statements}

    def statements(self, children):
        return self.transform_children(children)

    def workflow_stmt(self, children):
        return self.transform(children[0])

    def start_stmt(self, children):
        return self.transform(children[0])

    def end_stmt(self, children):
        return self.transform(children[0])

    def intent_stmt(self, children):
        agent = children[0]
        arg_list = self.transform(children[1])
        name = arg_list[0]
        input_ = arg_list[1] if len(arg_list) > 1 else None
        output = arg_list[2] if len(arg_list) > 2 else None
        return {'type': 'Intent', 'agent': agent, 'name': name, 'input': input_, 'output': output}

    def arg_list(self, children):
        name = self.transform(children[0])
        input_arg = self.transform(children[1]) if len(children) > 1 else None
        output_arg = self.transform(children[2]) if len(children) > 2 else None
        input_ = input_arg['input'] if input_arg and isinstance(input_arg, dict) else None
        output = output_arg['output'] if output_arg and isinstance(output_arg, dict) else None
        return [name, input_, output]

    def input_arg(self, children):
        return {'input': children[0]}

    def output_arg(self, children):
        return {'output': children[0]}

    def connect_stmt(self, children):
        from_ = children[0]
        to_ = children[1]
        options = children[2]
        return {'type': 'Connect', 'from': from_, 'to': to_, 'options': options}

    def options(self, children):
        opts = {}
        for child in children:
            opt_dict = self.transform(child)
            opts.update(opt_dict)
        return opts

    def connect_opt(self, children):
        return self.transform(children[0])

    def async_opt(self, children):
        return {'async': True}

    def timeout_opt(self, children):
        return {'timeout': children[0]}

    def run_decl(self, children):
        orch = children[0]
        wf = children[1]
        return {'type': 'Run', 'orchestrator': orch, 'workflow': wf}

    def array(self, children):
        return children[0]

    def strings(self, children):
        return self.transform_children(children)

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