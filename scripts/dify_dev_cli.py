import os
import sys
import json
import argparse
import subprocess
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

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

def format_timestamp(ts):
    if not ts:
        return "N/A"
    try:
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return str(ts)

def print_table(headers, rows):
    if not rows:
        print("No data available.")
        return
    widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            widths[idx] = max(widths[idx], len(str(val)))
            
    header_line = " | ".join(f"{h:<{widths[idx]}}" for idx, h in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))
    
    for row in rows:
        print(" | ".join(f"{str(val):<{widths[idx]}}" for idx, val in enumerate(row)))

def parse_sse_line(line):
    if line.startswith('data: '):
        try:
            return json.loads(line[6:])
        except:
            pass
    return None

def run_draft(app_id, inputs, files=[]):
    url = f"{BASE_URL}/console/api/apps/{app_id}/workflows/draft/run"
    payload = json.dumps({'inputs': inputs, 'files': files}).encode()
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
    import_parser.add_argument("--app-id", help="Override App ID to update an existing app")
    import_parser.add_argument("--description", help="App description override")
    import_parser.add_argument("--icon", help="App icon override (emoji)")
    import_parser.add_argument("--icon-background", help="App icon background color override hex (e.g. #000000)")

    # Test Run
    test_parser = subparsers.add_parser("test", help="Run draft workflow")
    test_parser.add_argument("--app-id", required=True, help="App ID")
    test_parser.add_argument("--inputs", default="{}", help="Inputs as JSON string")
    test_parser.add_argument("--files", default="[]", help="Input files as JSON string for multimodal/vision workflows")

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

    # List Apps
    list_apps_parser = subparsers.add_parser("list-apps", help="List apps in the workspace")
    list_apps_parser.add_argument("--page", type=int, default=1, help="Page number")
    list_apps_parser.add_argument("--limit", type=int, default=50, help="Items per page")
    list_apps_parser.add_argument("--name", help="Filter apps by name (search query)")
    list_apps_parser.add_argument("--mode", help="Filter apps by mode (e.g. workflow, chat)")

    # Export
    export_parser = subparsers.add_parser("export", help="Export app DSL (YAML)")
    export_parser.add_argument("--app-id", required=True, help="App ID")
    export_parser.add_argument("--output", "-o", help="Output file path (prints to stdout if not specified)")

    # List Runs
    list_runs_parser = subparsers.add_parser("list-runs", help="List workflow runs for an app")
    list_runs_parser.add_argument("--app-id", required=True, help="App ID")
    list_runs_parser.add_argument("--limit", type=int, default=20, help="Number of runs to retrieve")
    list_runs_parser.add_argument("--page", type=int, default=1, help="Page number")
    list_runs_parser.add_argument("--status", help="Filter runs by status (succeeded, failed, running, stopped)")

    # API Keys Management
    list_keys_parser = subparsers.add_parser("list-keys", help="List API keys for an app")
    list_keys_parser.add_argument("--app-id", required=True, help="App ID")

    create_key_parser = subparsers.add_parser("create-key", help="Create an API key for an app")
    create_key_parser.add_argument("--app-id", required=True, help="App ID")

    delete_key_parser = subparsers.add_parser("delete-key", help="Delete an API key for an app")
    delete_key_parser.add_argument("--app-id", required=True, help="App ID")
    delete_key_parser.add_argument("--key-id", required=True, help="Key ID")

    # MCP Management
    subparsers.add_parser("list-mcp", help="List MCP tool providers")

    add_mcp_parser = subparsers.add_parser("add-mcp", help="Register an MCP tool provider")
    add_mcp_parser.add_argument("--name", required=True, help="Name of the MCP provider")
    add_mcp_parser.add_argument("--url", required=True, help="SSE Server URL")
    add_mcp_parser.add_argument("--identifier", required=True, help="Unique server identifier")
    add_mcp_parser.add_argument("--icon", default="🔌", help="Emoji icon")
    add_mcp_parser.add_argument("--headers", help="Additional headers as JSON or Key=Value pairs")
    add_mcp_parser.add_argument("--timeout", type=float, default=30.0, help="HTTP connection timeout in seconds")
    add_mcp_parser.add_argument("--sse-timeout", type=float, default=300.0, help="SSE stream read timeout in seconds")

    delete_mcp_parser = subparsers.add_parser("delete-mcp", help="Delete an MCP tool provider")
    delete_mcp_parser.add_argument("--provider-id", required=True, help="Provider UUID, name or identifier")

    # Show App
    show_app_parser = subparsers.add_parser("show-app", help="Get app metadata details")
    show_app_parser.add_argument("--app-id", required=True, help="App ID")

    # Stop Run
    stop_run_parser = subparsers.add_parser("stop-run", help="Force stop a running workflow execution")
    stop_run_parser.add_argument("--app-id", required=True, help="App ID")
    stop_run_parser.add_argument("--run-id", required=True, help="Workflow Run ID")

    # List Model Providers
    subparsers.add_parser("list-models", help="List active model providers and models in workspace")

    # Update MCP provider
    update_mcp_parser = subparsers.add_parser("update-mcp", help="Update an existing MCP tool provider")
    update_mcp_parser.add_argument("--provider-id", required=True, help="Provider UUID, name or identifier")
    update_mcp_parser.add_argument("--name", help="New name of the MCP provider")
    update_mcp_parser.add_argument("--url", help="New SSE Server URL")
    update_mcp_parser.add_argument("--identifier", help="New server identifier")
    update_mcp_parser.add_argument("--icon", help="New emoji icon")
    update_mcp_parser.add_argument("--headers", help="New headers as JSON or Key=Value pairs")
    update_mcp_parser.add_argument("--timeout", type=float, help="New HTTP connection timeout in seconds")
    update_mcp_parser.add_argument("--sse-timeout", type=float, help="New SSE stream read timeout in seconds")

    # Check Dependencies
    check_deps_parser = subparsers.add_parser("check-deps", help="Check dependencies of an app")
    check_deps_parser.add_argument("--app-id", required=True, help="App ID")

    # Default Model Management
    get_def_model_parser = subparsers.add_parser("get-default-model", help="Get workspace default model for a type")
    get_def_model_parser.add_argument("--model-type", required=True, choices=["llm", "text-embedding", "rerank", "speech2text", "text2speech", "moderation"], help="Model type")

    set_def_model_parser = subparsers.add_parser("set-default-model", help="Set workspace default model for a type")
    set_def_model_parser.add_argument("--model-type", required=True, choices=["llm", "text-embedding", "rerank", "speech2text", "text2speech", "moderation"], help="Model type")
    set_def_model_parser.add_argument("--model", required=True, help="Model name/identifier")
    set_def_model_parser.add_argument("--provider", required=True, help="Provider slug")

    # Model Credentials Management
    get_model_creds_parser = subparsers.add_parser("get-model-credentials", help="Get credentials of a model provider")
    get_model_creds_parser.add_argument("--provider", required=True, help="Provider slug")

    set_model_creds_parser = subparsers.add_parser("set-model-credentials", help="Set credentials of a model provider")
    set_model_creds_parser.add_argument("--provider", required=True, help="Provider slug")
    set_model_creds_parser.add_argument("--credentials", required=True, help="Credentials in JSON format")
    set_model_creds_parser.add_argument("--name", help="Name of the credentials set")

    val_model_creds_parser = subparsers.add_parser("validate-model-credentials", help="Validate credentials of a model provider")
    val_model_creds_parser.add_argument("--provider", required=True, help="Provider slug")
    val_model_creds_parser.add_argument("--credentials", required=True, help="Credentials in JSON format")

    # Draft JSON management
    get_draft_json_parser = subparsers.add_parser("get-draft-json", help="Get draft raw JSON graph of an app")
    get_draft_json_parser.add_argument("--app-id", required=True, help="App ID")
    get_draft_json_parser.add_argument("--output", "-o", help="Output file path (prints to stdout if not specified)")

    update_draft_json_parser = subparsers.add_parser("update-draft-json", help="Update draft raw JSON graph of an app")
    update_draft_json_parser.add_argument("--app-id", required=True, help="App ID")
    update_draft_json_parser.add_argument("--file", "-i", required=True, help="Input file path containing new JSON graph")

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
        if args.app_id:
            payload['app_id'] = args.app_id
        if args.description:
            payload['description'] = args.description
        if args.icon:
            payload['icon'] = args.icon
            payload['icon_type'] = 'emoji'
        if args.icon_background:
            payload['icon_background'] = args.icon_background
            
        res = api_call('/console/api/apps/imports', 'POST', payload)
        if args.app_id:
            print(f"App updated successfully. ID: {res.get('app_id')}")
        else:
            print(f"App imported successfully. ID: {res.get('app_id')}")

    elif args.command == "test":
        try:
            inputs_dict = json.loads(args.inputs)
        except json.JSONDecodeError:
            print("Error: inputs must be a valid JSON string", file=sys.stderr)
            sys.exit(1)
        try:
            files_list = json.loads(args.files)
        except json.JSONDecodeError:
            print("Error: files must be a valid JSON string", file=sys.stderr)
            sys.exit(1)
        run_draft(args.app_id, inputs_dict, files_list)

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

    elif args.command == "list-apps":
        url = f'/console/api/apps?page={args.page}&limit={args.limit}'
        if args.name:
            url += f'&name={urllib.parse.quote(args.name)}'
        if args.mode:
            url += f'&mode={args.mode}'
        res = api_call(url)
        apps = res.get('data', [])
        headers = ['ID', 'Name', 'Mode', 'Description', 'Created At']
        rows = []
        for app in apps:
            desc = app.get('description') or ""
            if len(desc) > 30:
                desc = desc[:27] + "..."
            rows.append([
                app.get('id'),
                app.get('name'),
                app.get('mode'),
                desc,
                format_timestamp(app.get('created_at'))
            ])
        print_table(headers, rows)

    elif args.command == "export":
        res = api_call(f'/console/api/apps/{args.app_id}/export')
        yaml_content = res.get('data', '')
        if args.output:
            with open(args.output, 'w') as f:
                f.write(yaml_content)
            print(f"App DSL exported to {args.output} successfully.")
        else:
            print(yaml_content)

    elif args.command == "list-runs":
        url = f'/console/api/apps/{args.app_id}/workflow-runs?page={args.page}&limit={args.limit}'
        if args.status:
            url += f'&status={args.status.lower()}'
        res = api_call(url)
        runs = res.get('data', [])
        headers = ['Run ID', 'Status', 'Steps', 'Tokens', 'Elapsed (s)', 'Created At']
        rows = []
        for run in runs:
            rows.append([
                run.get('id'),
                run.get('status', '').upper(),
                run.get('total_steps', 0),
                run.get('total_tokens', 0),
                f"{run.get('elapsed_time', 0.0):.2f}" if run.get('elapsed_time') is not None else "0.00",
                format_timestamp(run.get('created_at'))
            ])
        print_table(headers, rows)

    elif args.command == "list-keys":
        res = api_call(f'/console/api/apps/{args.app_id}/api-keys')
        keys = res.get('data', [])
        headers = ['Key ID', 'Token', 'Type', 'Created At']
        rows = []
        for k in keys:
            rows.append([
                k.get('id'),
                k.get('token'),
                k.get('type'),
                format_timestamp(k.get('created_at'))
            ])
        print_table(headers, rows)

    elif args.command == "create-key":
        res = api_call(f'/console/api/apps/{args.app_id}/api-keys', 'POST', {})
        print(f"API Key created successfully:")
        print(f"  ID: {res.get('id')}")
        print(f"  Token: {res.get('token')}")
        print(f"  Type: {res.get('type')}")

    elif args.command == "delete-key":
        api_call(f'/console/api/apps/{args.app_id}/api-keys/{args.key_id}', 'DELETE')
        print(f"API Key {args.key_id} deleted successfully.")

    elif args.command == "list-mcp":
        providers = api_call('/console/api/workspaces/current/tool-providers')
        mcp_providers = [p for p in providers if p.get('type') == 'mcp' or p.get('provider_type') == 'mcp']
        headers = ['ID', 'Identifier', 'Name', 'URL', 'Tools Count']
        rows = []
        for p in mcp_providers:
            tools_count = len(p.get('tools', []))
            rows.append([
                p.get('id'),
                p.get('server_identifier'),
                p.get('name'),
                p.get('server_url') or p.get('configuration', {}).get('server_url') or "N/A",
                tools_count
            ])
        print_table(headers, rows)

    elif args.command == "add-mcp":
        headers_dict = {}
        if args.headers:
            try:
                headers_dict = json.loads(args.headers)
            except json.JSONDecodeError:
                for pair in args.headers.split(','):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        headers_dict[k.strip()] = v.strip()
                    else:
                        print(f"Warning: Invalid header pair format '{pair}', expected Key=Value", file=sys.stderr)
        payload = {
            'server_url': args.url,
            'name': args.name,
            'icon': args.icon,
            'icon_type': 'emoji',
            'icon_background': '#000000',
            'server_identifier': args.identifier,
            'configuration': {
                'timeout': args.timeout,
                'sse_read_timeout': args.sse_timeout
            },
            'headers': headers_dict,
            'authentication': None,
            'identity_mode': 'off'
        }
        res = api_call('/console/api/workspaces/current/tool-provider/mcp', 'POST', payload)
        print(f"MCP provider '{args.name}' registered successfully.")
        print(f"  ID: {res.get('id')}")
        print(f"  Identifier: {res.get('server_identifier')}")
        print(f"  Tools: {', '.join([t.get('name') for t in res.get('tools', [])])}")

    elif args.command == "delete-mcp":
        provider_id = args.provider_id
        providers = api_call('/console/api/workspaces/current/tool-providers')
        mcp_providers = [p for p in providers if p.get('type') == 'mcp' or p.get('provider_type') == 'mcp']
        found_uuid = None
        for p in mcp_providers:
            if p.get('id') == provider_id or p.get('server_identifier') == provider_id or p.get('name') == provider_id:
                found_uuid = p.get('id')
                break

        if not found_uuid:
            print(f"Error: MCP provider with ID, Identifier, or Name '{provider_id}' not found.", file=sys.stderr)
            sys.exit(1)

        payload = {
            'provider_id': found_uuid
        }
        api_call('/console/api/workspaces/current/tool-provider/mcp', 'DELETE', payload)
        print(f"MCP provider '{provider_id}' (ID: {found_uuid}) deleted successfully.")

    elif args.command == "show-app":
        res = api_call(f'/console/api/apps/{args.app_id}')
        print("App Details:")
        print(f"  ID:          {res.get('id')}")
        print(f"  Name:        {res.get('name')}")
        print(f"  Mode:        {res.get('mode')}")
        print(f"  Description: {res.get('description') or 'None'}")
        print(f"  Icon:        {res.get('icon')} (background: {res.get('icon_background')})")
        print(f"  API Enabled: {res.get('enable_api')}")
        print(f"  API URL:     {res.get('api_base_url')}")
        print(f"  Created At:  {format_timestamp(res.get('created_at'))}")
        print(f"  Updated At:  {format_timestamp(res.get('updated_at'))}")
        if res.get('site'):
            print(f"  Site URL:    {res.get('site', {}).get('app_base_url')}/workflow/{res.get('site', {}).get('access_token')}")

    elif args.command == "stop-run":
        res = api_call(f'/console/api/apps/{args.app_id}/workflow-runs/{args.run_id}/stop', 'POST', {})
        print(f"Workflow run {args.run_id} stopped successfully. Result: {res.get('result', 'success')}")

    elif args.command == "list-models":
        res = api_call('/console/api/workspaces/current/model-providers')
        providers = res.get('data', [])
        headers = ['Provider', 'Model Name', 'Type', 'Status']
        rows = []
        for p in providers:
            is_active = (p.get('custom_configuration', {}).get('status') == 'active' or 
                         p.get('system_configuration', {}).get('enabled') is True)
            if is_active:
                provider_slug = p.get('provider')
                provider_name = p.get('label', {}).get('en_US') or p.get('label', {}).get('zh_Hans') or provider_slug
                try:
                    models_res = api_call(f'/console/api/workspaces/current/model-providers/{provider_slug}/models')
                    for model in models_res.get('data', []):
                        rows.append([
                            provider_name,
                            model.get('model'),
                            model.get('model_type').upper(),
                            model.get('status').upper()
                        ])
                except Exception as e:
                    print(f"Warning: Failed to fetch models for provider {provider_slug}: {e}", file=sys.stderr)
        print_table(headers, rows)

    elif args.command == "update-mcp":
        provider_id = args.provider_id
        providers = api_call('/console/api/workspaces/current/tool-providers')
        mcp_providers = [p for p in providers if p.get('type') == 'mcp' or p.get('provider_type') == 'mcp']
        
        found_provider = None
        for p in mcp_providers:
            if p.get('id') == provider_id or p.get('server_identifier') == provider_id or p.get('name') == provider_id:
                found_provider = p
                break

        if not found_provider:
            print(f"Error: MCP provider with ID, Identifier, or Name '{provider_id}' not found.", file=sys.stderr)
            sys.exit(1)

        icon_data = found_provider.get('icon')
        if isinstance(icon_data, dict):
            existing_icon = icon_data.get('content')
            existing_bg = icon_data.get('background') or '#000000'
        else:
            existing_icon = icon_data
            existing_bg = found_provider.get('icon_background') or '#000000'

        name = args.name or found_provider.get('name')
        url = args.url or found_provider.get('server_url') or found_provider.get('configuration', {}).get('server_url')
        identifier = args.identifier or found_provider.get('server_identifier')
        icon = args.icon or existing_icon or "🔌"
        icon_bg = existing_bg
        
        headers_dict = found_provider.get('masked_headers') or {}
        if args.headers:
            try:
                headers_dict = json.loads(args.headers)
            except json.JSONDecodeError:
                headers_dict = {}
                for pair in args.headers.split(','):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        headers_dict[k.strip()] = v.strip()
                    else:
                        print(f"Warning: Invalid header pair format '{pair}', expected Key=Value", file=sys.stderr)

        existing_config = found_provider.get('configuration') or {}
        existing_timeout = existing_config.get('timeout') or 30.0
        existing_sse = existing_config.get('sse_read_timeout') or 300.0
        timeout = args.timeout if args.timeout is not None else existing_timeout
        sse_timeout = args.sse_timeout if args.sse_timeout is not None else existing_sse

        payload = {
            'provider_id': found_provider.get('id'),
            'server_url': url,
            'name': name,
            'icon': icon,
            'icon_type': 'emoji',
            'icon_background': icon_bg,
            'server_identifier': identifier,
            'configuration': {
                'timeout': timeout,
                'sse_read_timeout': sse_timeout
            },
            'headers': headers_dict,
            'authentication': None,
            'identity_mode': 'off'
        }
        res = api_call('/console/api/workspaces/current/tool-provider/mcp', 'PUT', payload)
        print(f"MCP provider '{name}' updated successfully.")

    elif args.command == "check-deps":
        res = api_call(f'/console/api/apps/imports/{args.app_id}/check-dependencies')
        deps = res.get('leaked_dependencies', [])
        if not deps:
            print("All dependencies are satisfied. No missing models, datasets, or MCP servers found.")
        else:
            print("Warning: Found missing dependencies:")
            for d in deps:
                print(f"  - [{d.get('type')}] {d.get('name')} (ID/Identifier: {d.get('id')})")

    elif args.command == "get-default-model":
        res = api_call(f'/console/api/workspaces/current/default-model?model_type={args.model_type}')
        data = res.get('data') or {}
        print("Default Model Configuration:")
        print(f"  Model Type: {args.model_type}")
        provider_data = data.get('provider')
        provider_slug = provider_data.get('provider') if isinstance(provider_data, dict) else provider_data
        print(f"  Provider:   {provider_slug or 'None'}")
        print(f"  Model:      {data.get('model') or 'None'}")

    elif args.command == "set-default-model":
        payload = {
            "model_settings": [
                {
                    "model_type": args.model_type,
                    "model": args.model,
                    "provider": args.provider
                }
            ]
        }
        api_call('/console/api/workspaces/current/default-model', 'POST', payload)
        print(f"Default model for type '{args.model_type}' successfully updated to '{args.model}' (provider: '{args.provider}').")

    elif args.command == "get-model-credentials":
        res = api_call(f'/console/api/workspaces/current/model-providers/{args.provider}/credentials')
        print(json.dumps(res, indent=2, ensure_ascii=False))

    elif args.command == "set-model-credentials":
        try:
            creds_dict = json.loads(args.credentials)
        except json.JSONDecodeError:
            print("Error: credentials must be a valid JSON string", file=sys.stderr)
            sys.exit(1)
        payload = {
            "credentials": creds_dict
        }
        if args.name:
            payload["name"] = args.name
        api_call(f'/console/api/workspaces/current/model-providers/{args.provider}/credentials', 'POST', payload)
        print(f"Credentials for model provider '{args.provider}' successfully set.")

    elif args.command == "validate-model-credentials":
        try:
            creds_dict = json.loads(args.credentials)
        except json.JSONDecodeError:
            print("Error: credentials must be a valid JSON string", file=sys.stderr)
            sys.exit(1)
        payload = {
            "credentials": creds_dict
        }
        res = api_call(f'/console/api/workspaces/current/model-providers/{args.provider}/credentials/validate', 'POST', payload)
        result = res.get('result', 'error')
        if result == 'success':
            print(f"Credentials validation for provider '{args.provider}' SUCCEEDED.")
        else:
            print(f"Credentials validation for provider '{args.provider}' FAILED: {res.get('error', 'Unknown validation error')}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "get-draft-json":
        res = api_call(f'/console/api/apps/{args.app_id}/workflows/draft')
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(res, f, indent=2, ensure_ascii=False)
            print(f"Draft JSON exported to {args.output} successfully.")
        else:
            print(json.dumps(res, indent=2, ensure_ascii=False))

    elif args.command == "update-draft-json":
        if not os.path.exists(args.file):
            print(f"Error: File {args.file} not found", file=sys.stderr)
            sys.exit(1)
        with open(args.file) as f:
            try:
                new_data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON file: {e}", file=sys.stderr)
                sys.exit(1)

        current_draft = api_call(f'/console/api/apps/{args.app_id}/workflows/draft')
        
        new_graph = new_data.get('graph') if isinstance(new_data, dict) and 'graph' in new_data else new_data
        
        payload = {
            'graph': new_graph,
            'features': new_data.get('features') if isinstance(new_data, dict) and 'features' in new_data else current_draft.get('features', {}),
            'hash': current_draft.get('hash'),
            'environment_variables': new_data.get('environment_variables') if isinstance(new_data, dict) and 'environment_variables' in new_data else current_draft.get('environment_variables', []),
            'conversation_variables': new_data.get('conversation_variables') if isinstance(new_data, dict) and 'conversation_variables' in new_data else current_draft.get('conversation_variables', [])
        }
        res = api_call(f'/console/api/apps/{args.app_id}/workflows/draft', 'POST', payload)
        print(f"Draft JSON graph updated successfully. New hash: {res.get('hash')}")

if __name__ == '__main__':
    main()
