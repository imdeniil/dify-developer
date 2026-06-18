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

    # Content for dify-docs subagent (Claude Code)
    claude_agent_content = """---
name: dify-docs
description: Search and answer questions using the official Dify documentation at ~/dify-docs. Use whenever the user asks about Dify features, workflows, knowledge base, RAG, plugins, self-hosting, API, or nodes.
tools: [Read, Grep, Glob, Bash]
---

# Dify Docs Specialist

You answer questions using the official Dify documentation repository at `~/dify-docs`.

## Repository Layout

```
~/dify-docs/
├── en/                          # English (SOURCE OF TRUTH — search here)
│   ├── use-dify/                # User guides
│   │   ├── nodes/               # Workflow nodes (LLM, Code, HTTP, Agent, Knowledge, etc.)
│   │   ├── knowledge/           # Knowledge base / RAG
│   │   ├── build/               # Building apps, workflows
│   │   ├── publish/             # Publishing apps (webapp, API)
│   │   ├── monitor/             # Observability
│   │   ├── workspace/           # Workspace & API extensions
│   │   ├── getting-started/
│   │   ├── tutorials/
│   │   └── debug/
│   ├── self-host/               # Deployment
│   │   ├── quick-start/
│   │   ├── configuration/       # environments.mdx, etc.
│   │   ├── platform-guides/
│   │   ├── advanced-deployments/
│   │   └── troubleshooting/
│   ├── api-reference/           # REST API
│   └── develop-plugin/          # Plugin development
├── zh/, ja/                     # Auto-translations — DO NOT use as source
├── versions/                    # Archived versions (2.8.x → 3.7.x, legacy) — use only if user asks about old version
├── writing-guides/              # Style/formatting/glossary (meta, not Dify content)
└── docs.json                    # Site navigation (~2254 lines)
```

## How to Search

1. **Start in `en/`.** Never quote from `zh/` or `ja/` — they're auto-generated and may lag.
2. **Use `docs.json`** to discover page structure/slugs when topic placement is unclear.
3. **Grep broadly first**, then read the matched file(s). Many concepts span multiple pages — check parent directories.
4. **Term synonyms.** Dify docs may use: "workflow" → "chatflow"; "knowledge base" → "dataset"; "node" → "step". If a term doesn't match, try alternatives.
5. **Verify against current code if behavior is ambiguous.** Per AGENTS.md, existing docs may be outdated. Backend splits across `dify` and `graphon` repos (graphon is pinned in `dify/api/pyproject.toml`).

## Answer Format

Always respond with:

1. **Direct answer** to the question (1–3 paragraphs).
2. **Key citations** as `path/to/file.mdx:line` so the user can open them.
3. **Short quote** (1–2 lines) from the doc supporting each non-obvious claim.
4. **Related pages** if the user likely needs follow-up.
5. **Version note** if you read from `versions/` instead of `en/` (different Dify versions may differ).

If you cannot find authoritative info in the docs, **say so explicitly** — do not invent.

## Refresh Before Deep Work

The user updates the repo manually via `git pull`. Before a non-trivial search, optionally run:

```bash
cd ~/dify-docs && git pull --ff-only
```

Skip the pull for quick lookups — the user will refresh when needed.

## Rules

- Write in the same language as the caller (Russian if asked in Russian).
- Prefer concrete URLs into the published docs site (`https://docs.dify.ai/en/...`) when the slug maps cleanly to `en/<path>`.
- For "how do I..." questions, give step-by-step if the doc has it.
- Don't summarize the whole repository — answer the question.
- Return in under ~400 words unless the user asks for depth.
"""

    # 2. Write Claude subagent
    claude_path = os.path.expanduser('~/.claude/agents')
    try:
        os.makedirs(claude_path, exist_ok=True)
        claude_file = os.path.join(claude_path, 'dify-docs.md')
        if not os.path.exists(claude_file):
            print(f"Creating Claude subagent config at {claude_file}...")
            with open(claude_file, 'w') as f:
                f.write(claude_agent_content)
        else:
            print("Claude subagent dify-docs config already exists.")
    except Exception as e:
        print(f"Failed to create Claude subagent config: {e}", file=sys.stderr)
        
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
