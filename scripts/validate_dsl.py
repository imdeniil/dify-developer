#!/usr/bin/env python3
import sys
import os
import json
import subprocess

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_dsl.py <path_to_yaml_dsl>")
        sys.exit(1)
        
    yaml_path = sys.argv[1]
    if not os.path.exists(yaml_path):
        print(f"Error: File '{yaml_path}' not found", file=sys.stderr)
        sys.exit(1)
        
    with open(yaml_path, 'r', encoding='utf-8') as f:
        yaml_content = f.read()
    
    # Python validation script that runs inside docker-api-1 container
    validation_script = """import sys
import json
import yaml
from pydantic import ValidationError

# Define class mappings
mapping = {
    'start': ('graphon.nodes.start.entities', 'StartNodeData'),
    'end': ('graphon.nodes.end.entities', 'EndNodeData'),
    'answer': ('graphon.nodes.answer.entities', 'AnswerNodeData'),
    'code': ('graphon.nodes.code.entities', 'CodeNodeData'),
    'http-request': ('graphon.nodes.http_request.entities', 'HttpRequestNodeData'),
    'if-else': ('graphon.nodes.if_else.entities', 'IfElseNodeData'),
    'llm': ('graphon.nodes.llm.entities', 'LLMNodeData'),
    'question-classifier': ('graphon.nodes.question_classifier.entities', 'QuestionClassifierNodeData'),
    'parameter-extractor': ('graphon.nodes.parameter_extractor.entities', 'ParameterExtractorNodeData'),
    'list-operator': ('graphon.nodes.list_operator.entities', 'ListOperatorNodeData'),
    'iteration': ('graphon.nodes.iteration.entities', 'IterationNodeData'),
    'loop': ('graphon.nodes.loop.entities', 'LoopNodeData'),
    'document-extractor': ('graphon.nodes.document_extractor.entities', 'DocumentExtractorNodeData'),
    'template-transform': ('graphon.nodes.template_transform.entities', 'TemplateTransformNodeData'),
    'variable-aggregator': ('graphon.nodes.variable_aggregator.entities', 'VariableAggregatorNodeData'),
    'variable-assigner': ('graphon.nodes.variable_assigner.v2.entities', 'VariableAssignerNodeData'),
    'human-input': ('graphon.nodes.human_input.entities', 'HumanInputNodeData'),
    'tool': ('graphon.nodes.tool.entities', 'ToolNodeData'),
    'knowledge-retrieval': ('core.workflow.nodes.knowledge_retrieval.entities', 'KnowledgeRetrievalNodeData'),
    'agent': ('core.workflow.nodes.agent.entities', 'DifyAgentNodeData'),
}

# Add /app/api to sys.path to resolve core imports
if '/app/api' not in sys.path:
    sys.path.insert(0, '/app/api')

errors = []
try:
    yaml_content = sys.stdin.read()
    dsl_data = yaml.safe_load(yaml_content)
except Exception as e:
    errors.append(f"YAML syntax error: {e}")
    print(json.dumps(errors))
    sys.exit(0)

if not isinstance(dsl_data, dict):
    errors.append("Invalid DSL format: root must be a mapping.")
    print(json.dumps(errors))
    sys.exit(0)

workflow = dsl_data.get('workflow', dsl_data)
graph = workflow.get('graph', {})
nodes = graph.get('nodes', [])

if not nodes:
    errors.append("Missing or empty 'workflow.graph.nodes' in YAML.")
    print(json.dumps(errors))
    sys.exit(0)

for node in nodes:
    node_id = node.get('id')
    node_data = node.get('data', {})
    node_type = node_data.get('type')
    
    if not node_type:
        errors.append(f"Node '{node_id}' is missing 'data.type'.")
        continue
        
    cls_info = mapping.get(node_type)
    if not cls_info:
        # Warning/skip if not in mapping (e.g. custom plugins)
        continue
        
    module_path, class_name = cls_info
    try:
        module = __import__(module_path, fromlist=[class_name])
        node_class = getattr(module, class_name)
    except Exception as e:
        errors.append(f"Internal: Failed to load validator for node type '{node_type}': {e}")
        continue
        
    try:
        node_class.model_validate(node_data)
    except ValidationError as e:
        for err in e.errors():
            loc_str = ' -> '.join(str(loc) for loc in err['loc'])
            errors.append(f"Node '{node_id}' ({node_type}) validation error at '{loc_str}': {err['msg']} (input: {err.get('input')})")

print(json.dumps(errors))
"""
    
    # Run the validation script inside docker-api-1 container
    cmd = ["docker", "exec", "-i", "docker-api-1", "python", "-c", validation_script]
    try:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(input=yaml_content)
    except Exception as e:
        print(f"Error running validator in docker container: {e}", file=sys.stderr)
        sys.exit(1)
        
    if process.returncode != 0:
        print(f"Docker exec error: {stderr}", file=sys.stderr)
        sys.exit(1)
        
    try:
        errors_list = json.loads(stdout.strip())
    except Exception as e:
        print(f"Error parsing validator output: {stdout}\nStderr: {stderr}", file=sys.stderr)
        sys.exit(1)
        
    if errors_list:
        print("❌ DSL Validation Failed:")
        for err in errors_list:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("✅ DSL Validation Succeeded! All nodes match their Dify Pydantic schemas.")
        sys.exit(0)

if __name__ == '__main__':
    main()
