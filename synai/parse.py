from lark import Lark, Transformer
import json

grammar = r'''
start: program

program: declaration+

declaration: orchestrator_decl | run_decl

orchestrator_decl: "orchestrator" STRING "{" block+ "}"
block: agents_block | workflow_block
agents_block: "agents" "{" agent_entry+ "}"
agent_entry: ID ":" AGENT_TYPE "{" property* "}"
property: model_prop | capabilities_prop | other_prop
model_prop: "model:" STRING
capabilities_prop: "capabilities:" array
other_prop: "endpoint:" STRING | "transport:" STRING | "local:" "true" | "auth:" STRING
workflow_block: "workflow" STRING "{" workflow_stmt+ "}"
workflow_stmt: start_stmt | connect_stmt | end_stmt
start_stmt: "start:" intent_stmt
end_stmt: "end:" intent_stmt
intent_stmt: agent_id "." "intent" "(" intent_name ("," input_arg)? ("," output_arg)? ")"
agent_id: ID
intent_name: STRING
input_arg: "input:" STRING
output_arg: "output:" STRING
connect_stmt: "connect" from_agent "." "output" "->" to_agent "." "input" "{" connect_opt* "}"
from_agent: ID
to_agent: ID
connect_opt: async_opt | timeout_opt
async_opt: "async:" "true"
timeout_opt: "timeout:" INT "s"
array: "[" STRING ("," STRING)* "]"
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
    def program(self, items):
        return {'type': 'Program', 'declarations': [self.visit(i) for i in items]}
    
    def orchestrator_decl(self, items):
        name = self.visit(items[1])
        blocks = self.visit(items[3]) if len(items) > 3 else []
        return {'type': 'Orchestrator', 'name': name, 'blocks': blocks}
    
    def agents_block(self, items):
        agents = self.visit(items[1]) if len(items) > 1 else []
        return {'type': 'AgentsBlock', 'agents': agents}
    
    def agent_entry(self, items):
        id_ = self.visit(items[0])
        agent_type = self.visit(items[2])
        properties = self.visit(items[4]) if len(items) > 4 else {}
        return {'type': 'Agent', 'id': id_, 'agent_type': agent_type, 'properties': properties}
    
    def property(self, items):
        return self.visit(items[0])
    
    def model_prop(self, items):
        return {'model': self.visit(items[1])}
    
    def capabilities_prop(self, items):
        return {'capabilities': self.visit(items[1])}
    
    def other_prop(self, items):
        key = items[0].rstrip(':')
        return {key: self.visit(items[1]) if len(items) > 1 else True}
    
    def workflow_block(self, items):
        name = self.visit(items[1])
        statements = self.visit(items[3]) if len(items) > 3 else []
        return {'type': 'Workflow', 'name': name, 'statements': statements}
    
    def workflow_stmt(self, items):
        return self.visit(items[0])
    
    def start_stmt(self, items):
        return self.visit(items[1])
    
    def end_stmt(self, items):
        return self.visit(items[1])
    
    def intent_stmt(self, items):
        agent = self.visit(items[0])
        name = self.visit(items[3])
        input_ = self.visit(items[5]) if len(items) > 4 else None
        output = self.visit(items[7]) if len(items) > 6 else None
        return {'type': 'Intent', 'agent': agent, 'name': name, 'input': input_, 'output': output}
    
    def connect_stmt(self, items):
        from_ = self.visit(items[1])
        to_ = self.visit(items[5])
        options = self.visit(items[7]) if len(items) > 7 else {}
        return {'type': 'Connect', 'from': from_, 'to': to_, 'options': options}
    
    def connect_opt(self, items):
        return self.visit(items[0])
    
    def async_opt(self, items):
        return {'async': True}
    
    def timeout_opt(self, items):
        return {'timeout': self.visit(items[1])}
    
    def run_decl(self, items):
        orch = self.visit(items[1])
        wf = self.visit(items[4])
        return {'type': 'Run', 'orchestrator': orch, 'workflow': wf}
    
    def array(self, items):
        return [self.visit(i) for i in items]
    
    def input_arg(self, items):
        return self.visit(items[1])
    
    def output_arg(self, items):
        return self.visit(items[1])
    
    def ID(self, s):
        return s.value
    
    def STRING(self, s):
        return s.value.strip('"')
    
    def INT(self, s):
        return int(s.value)

def parse_synai(code: str) -> dict:
    try:
        tree = parser.parse(code)
        transformer = SynTransformer()
        ast = transformer.transform(tree)
        return ast
    except Exception as e:
        raise ValueError(f"Parse error: {e}")

# Teste inline (rode python synai/parse.py para ver)
if __name__ == '__main__':
    with open('../examples/demo.synai', 'r') as f:
        code = f.read()
    ast = parse_synai(code)
    print(json.dumps(ast, indent=2))
