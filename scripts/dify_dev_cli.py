import os
import sys
import json
import argparse
import subprocess
import urllib.request
import urllib.error

# Load environment
ENV_FILE = '/home/keemor/defyproj/.env'
env_vars = {}
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    k, v = line.split('=', 1)
                    env_vars[k.strip()] = v.strip()
                except ValueError:
                    pass

BASE_URL = env_vars.get('DIFY_BASE_URL', 'http://localhost:3006')
TOKEN = env_vars.get('DIFY_CONSOLE_TOKEN')
WS_ID = env_vars.get('DIFY_WORKSPACE_ID')

if not TOKEN or not WS_ID:
    # Do not print warning during setup, since setup is designed to initialize things
    if 'setup' not in sys.argv:
        print("Warning: DIFY_CONSOLE_TOKEN or DIFY_WORKSPACE_ID is not configured in .env", file=sys.stderr)

headers = {
    'Authorization': f'Bearer {TOKEN}',
    'X-WORKSPACE-ID': WS_ID,
    'Content-Type': 'application/json'
}

def api_call(path, method='GET', payload=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode()
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"API Error {e.code} on {method} {path}: {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)

def parse_sse_line(line):
    if line.startswith('data: '):
        try:
            return json.loads(line[6:])
        except:
            pass
    return None

def run_draft(app_id, inputs):
    url = f"{BASE_URL}/console/api/apps/{app_id}/workflows/draft/run"
    payload = json.dumps({'inputs': inputs, 'files': []}).encode()
    req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
    
    print("Starting draft execution stream...")
    try:
        with urllib.request.urlopen(req) as resp:
            while True:
                line = resp.readline().decode()
                if not line:
                    break
                line = line.strip()
                event = parse_sse_line(line)
                if event:
                    handle_workflow_event(event)
    except Exception as e:
        print(f"Stream error: {e}", file=sys.stderr)

def get_events(run_id):
    url = f"{BASE_URL}/console/api/workflow/{run_id}/events?include_state_snapshot=true"
    req = urllib.request.Request(url, headers=headers, method='GET')
    
    print(f"Retrieving post-resume event log for Run ID {run_id}...")
    try:
        with urllib.request.urlopen(req) as resp:
            while True:
                line = resp.readline().decode()
                if not line:
                    break
                line = line.strip()
                event = parse_sse_line(line)
                if event:
                    handle_workflow_event(event)
    except Exception as e:
        print(f"Event retrieval error: {e}", file=sys.stderr)

def handle_workflow_event(event):
    ev = event.get('event')
    data = event.get('data', {})
    
    if ev == 'workflow_started':
        print(f"\n🚀 WORKFLOW STARTED (Run ID: {data.get('id')})")
    elif ev == 'node_started':
        print(f"  • Node [{data.get('title')}] ({data.get('node_type')}) started...")
    elif ev == 'node_finished':
        status = data.get('status')
        badge = "✅" if status == "succeeded" else "❌"
        print(f"  {badge} Node [{data.get('title')}] finished: {status}")
        if data.get('outputs'):
            print(f"    Outputs: {data.get('outputs')}")
        if data.get('error'):
            print(f"    Error: {data.get('error')}")
    elif ev == 'human_input_required':
        print(f"\n⚠️ HUMAN INPUT REQUIRED!")
        print(f"  Node: {data.get('node_title')} (ID: {data.get('node_id')})")
        print(f"  Content: {data.get('form_content')}")
        print(f"  Token: {data.get('form_token')}")
        print(f"  Actions: {', '.join([a.get('id') for a in data.get('actions', [])])}")
        print(f"  Expiration: {data.get('expiration_time')}")
        print(f"Use 'submit-form' command to provide response and resume execution.\n")
    elif ev == 'workflow_paused':
        print(f"⏸️ WORKFLOW PAUSED (Waiting for Human Input)\n")
    elif ev == 'workflow_finished':
        print(f"\n🏁 WORKFLOW FINISHED: {data.get('status')}")
        if data.get('outputs'):
            print(f"  Outputs: {data.get('outputs')}")

def run_setup():
    print("Initializing Dify Developer Environment...")
    
    # 1. Clone dify-docs if not exists
    docs_path = os.path.expanduser('~/dify-docs')
    if not os.path.exists(docs_path):
        print(f"Cloning Dify documentation into {docs_path}...")
        try:
            # depth 1 for fast cloning
            subprocess.run(["git", "clone", "--depth", "1", "https://github.com/langgenius/dify-docs.git", docs_path], check=True)
            print("Documentation cloned successfully.")
        except Exception as e:
            print(f"Failed to clone documentation: {e}", file=sys.stderr)
    else:
        print("Dify documentation already exists.")

    print("Environment setup completed successfully.")

def main():
    parser = argparse.ArgumentParser(description="Dify Workflow Developer CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup
    subparsers.add_parser("setup", help="Bootstrap development environment (docs & subagents)")

    # Import
    import_parser = subparsers.add_parser("import", help="Import app from YAML DSL")
    import_parser.add_argument("--file", required=True, help="Path to YAML DSL file")
    import_parser.add_argument("--name", help="Override app name")

    # Test Run
    test_parser = subparsers.add_parser("test", help="Run draft workflow")
    test_parser.add_argument("--app-id", required=True, help="App ID")
    test_parser.add_argument("--inputs", default="{}", help="Inputs as JSON string")

    # Submit Form
    submit_parser = subparsers.add_parser("submit-form", help="Submit Human Input form response")
    submit_parser.add_argument("--token", required=True, help="HITL Form Token")
    submit_parser.add_argument("--action", required=True, help="Selected Action ID (e.g. approve)")
    submit_parser.add_argument("--inputs", default="{}", help="Form inputs as JSON string")

    # Get events
    events_parser = subparsers.add_parser("get-events", help="Retrieve run events after resume")
    events_parser.add_argument("--run-id", required=True, help="Workflow Run ID")

    # Publish
    publish_parser = subparsers.add_parser("publish", help="Publish draft workflow")
    publish_parser.add_argument("--app-id", required=True, help="App ID")

    # Delete
    delete_parser = subparsers.add_parser("delete", help="Delete app from Dify")
    delete_parser.add_argument("--app-id", required=True, help="App ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "setup":
        run_setup()

    elif args.command == "import":
        if not os.path.exists(args.file):
            print(f"Error: File {args.file} not found", file=sys.stderr)
            sys.exit(1)
        with open(args.file) as f:
            yaml_content = f.read()
        payload = {
            'mode': 'yaml-content',
            'yaml_content': yaml_content
        }
        if args.name:
            payload['name'] = args.name
        res = api_call('/console/api/apps/imports', 'POST', payload)
        print(f"App imported successfully. ID: {res.get('app_id')}")

    elif args.command == "test":
        try:
            inputs_dict = json.loads(args.inputs)
        except json.JSONDecodeError:
            print("Error: inputs must be a valid JSON string", file=sys.stderr)
            sys.exit(1)
        run_draft(args.app_id, inputs_dict)

    elif args.command == "submit-form":
        try:
            inputs_dict = json.loads(args.inputs)
        except json.JSONDecodeError:
            print("Error: inputs must be a valid JSON string", file=sys.stderr)
            sys.exit(1)
        payload = {
            "action": args.action,
            "inputs": inputs_dict
        }
        res = api_call(f'/console/api/form/human_input/{args.token}', 'POST', payload)
        print("HITL Form submitted successfully.")

    elif args.command == "get-events":
        get_events(args.run_id)

    elif args.command == "publish":
        res = api_call(f'/console/api/apps/{args.app_id}/workflows/publish', 'POST', {'tool_published': False})
        print(f"Workflow published successfully. Result: {res.get('result')}")

    elif args.command == "delete":
        api_call(f'/console/api/apps/{args.app_id}', 'DELETE')
        print(f"App {args.app_id} deleted successfully.")

if __name__ == '__main__':
    main()
