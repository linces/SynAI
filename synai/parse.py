from lark import Lark, Transformer
import json

grammar = r'''
?start: program

program: declaration+

declaration: orchestrator_decl | run_decl

orchestrator_decl: "orchestrator" STRING "{" block+ "}"
block: agents_block | workflow_block
agents_block: "agents" "{" agent_entry+ "}"
agent_entry: ID ":" AGENT_TYPE "{" agent_property+ "}"
agent_property: property
workflow_block: "workflow" STRING "{" workflow_stmt+ "}"
workflow_stmt: "start:" intent_stmt | connect_stmt | "end:" intent_stmt
intent_stmt: agent_id "." "intent" "(" intent_name ("," "input:" expr)? ("," "output:" STRING)? ")"
agent_id: ID
intent_name: STRING
connect_stmt: "connect" agent_id "." "output" "->" agent_id "." "input" "{" connect_opt* "}"
connect_opt: "async:" "true" | "transform:" ID | "timeout:" INT "s" | "filter:" expr | "retry:" INT
property: "model:" STRING | "capabilities:" array | "endpoint:" STRING | "transport:" STRING | "local:" "true" | "auth:" STRING
array: "[" STRING ("," STRING)* "]?"

AGENT_TYPE: /[A-Z][a-zA-Z0-9]+/
ID: /[a-zA-Z_][a-zA-Z0-9_]*/
STRING: /"[^"]*"/
INT: /[0-9]+/
expr: STRING | ID "." field
field: "success" | "error" | "output"

run_decl: "run" STRING "with" "workflow" STRING

%import common.WS
%ignore WS
'''

parser = Lark(grammar, start='program')

class SynTransformer(Transformer):
    def program(self, items):
        return {'type': 'Program', 'declarations': items}
    
    def orchestrator_decl(self, items):
        name = items[0].value.strip('"')
        blocks = items[1]
        return {'type': 'Orchestrator', 'name': name, 'blocks': blocks}
    
    def agents_block(self, items):
        return {'type': 'AgentsBlock', 'agents': items}
    
    def agent_entry(self, items):
        id_ = items[0].value
        agent_type = items[1].value
        properties = {}
        for p in items[2:]:
            if isinstance(p, list) and len(p) >= 2:
                key = str(p[0]).split(':')[0].strip()
                if key == 'capabilities':
                    value = [str(v.value.strip('"')) for v in p[1] if hasattr(v, 'value')]
                else:
                    value = p[1].value if hasattr(p[1], 'value') else str(p[1])
                properties[key] = value
        return {'type': 'Agent', 'id': id_, 'agent_type': agent_type, 'properties': properties}
    
    def workflow_block(self, items):
        name = items[0].value.strip('"')
        stmts = items[1]
        return {'type': 'Workflow', 'name': name, 'statements': stmts}
    
    def intent_stmt(self, items):
        agent = items[0].value
        name = items[2].value.strip('"')
        input_ = None
        output = None
        i = 3
        while i < len(items):
            if str(items[i]) == ',':
                i += 1
            if i < len(items) and 'input:' in str(items[i]):
                input_ = items[i+1].value.strip('"') if i+1 < len(items) else None
                i += 2
            elif i < len(items) and 'output:' in str(items[i]):
                output = items[i+1].value.strip('"') if i+1 < len(items) else None
                i += 2
            else:
                i += 1
        return {'type': 'Intent', 'agent': agent, 'name': name, 'input': input_, 'output': output}
    
    def connect_stmt(self, items):
        from_agent = items[1].value
        to_agent = items[5].value
        opts = {}
        i = 7
        while i < len(items):
            if str(items[i]) == 'async:':
                opts['async'] = True
                i += 1
            elif str(items[i]) == 'transform:':
                opts['transform'] = items[i+1].value
                i += 2
            else:
                i += 1
        return {'type': 'Connect', 'from': from_agent, 'to': to_agent, 'options': opts}
    
    def run_decl(self, items):
        orch = items[1].value.strip('"')
        wf = items[4].value.strip('"')
        return {'type': 'Run', 'orchestrator': orch, 'workflow': wf}
    
    def ID(self, s): return s.value
    def STRING(self, s): return s.value.strip('"')
    def array(self, items): return [str(i.value.strip('"')) for i in items]
    def property(self, items): return {str(items[0]).split(':')[0]: items[1]}

def parse_synai(code: str) -> dict:
    try:
        tree = parser.parse(code)
        transformer = SynTransformer()
        ast = transformer.transform(tree)
        return ast
    except Exception as e:
        raise ValueError(f"Parse error: {e}")
