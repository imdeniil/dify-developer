#!/usr/bin/env python3
"""
Helper: обновить graph workflow через Console API.
Полный цикл GET → modify → POST с правильным hash.

Использование:
  python sync_workflow.py <app_id>
"""

import json
import sys
import urllib.request
import urllib.error


def get_draft(app_id: str, token: str, ws: str, base_url: str = "http://localhost:3006") -> dict:
    req = urllib.request.Request(
        f"{base_url}/console/api/apps/{app_id}/workflows/draft",
        headers={"Authorization": f"Bearer {token}", "X-WORKSPACE-ID": ws}
    )
    return json.loads(urllib.request.urlopen(req).read())


def sync_draft(app_id: str, token: str, ws: str, graph: dict, features: dict,
               environment_variables: list, conversation_variables: list,
               current_hash: str, base_url: str = "http://localhost:3006") -> dict:
    payload = {
        "graph": graph,
        "features": features,
        "hash": current_hash,
        "environment_variables": environment_variables,
        "conversation_variables": conversation_variables,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base_url}/console/api/apps/{app_id}/workflows/draft",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "X-WORKSPACE-ID": ws,
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode()}


def parse_sse_events(raw: str) -> list:
    """Parse SSE response from workflow run into list of event dicts."""
    events = []
    for line in raw.split('\n'):
        if line.startswith('data: '):
            try:
                events.append(json.loads(line[6:]))
            except (ValueError, json.JSONDecodeError):
                pass
    return events


def run_draft(app_id: str, token: str, ws: str, inputs: dict | None = None,
              files: list | None = None,
              base_url: str = "http://localhost:3006", timeout: int = 240) -> list:
    """Run draft workflow, return list of SSE events."""
    payload = json.dumps({"inputs": inputs or {}, "files": files or []}).encode()
    req = urllib.request.Request(
        f"{base_url}/console/api/apps/{app_id}/workflows/draft/run",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "X-WORKSPACE-ID": ws,
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return parse_sse_events(resp.read().decode())
    except urllib.error.HTTPError as e:
        return [{"event": "error", "data": {"error": f"HTTP {e.code}: {e.read().decode()[:500]}"}}]


def summarize_events(events: list) -> str:
    """Human-readable summary of workflow run events."""
    lines = []
    total_elapsed = 0
    for e in events:
        ev = e.get('event')
        data = e.get('data', {})
        if ev == 'node_finished':
            status = data.get('status')
            title = data.get('title', '')
            elapsed = data.get('elapsed_time', 0)
            total_elapsed += elapsed
            if status == 'failed':
                lines.append(f"  ✗ {title} FAILED: {data.get('error', '')[:200]}")
            else:
                tokens = (data.get('execution_metadata') or {}).get('total_tokens', 0)
                tinfo = f" tokens={tokens}" if tokens else ""
                lines.append(f"  ✓ {title} {elapsed:.1f}s{tinfo}")
                for k, v in list(data.get('outputs', {}).items())[:3]:
                    v_str = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
                    lines.append(f"      {k}: {v_str[:200]}")
        elif ev == 'workflow_finished':
            status = data.get('status')
            lines.append(f"\n=== WORKFLOW {status} (total: {total_elapsed:.1f}s) ===")
        elif ev in ('workflow_failed', 'error'):
            msg = data.get('error') or data.get('message')
            lines.append(f"✗ {ev}: {msg[:300]}")
    return '\n'.join(lines)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python sync_workflow.py <app_id>")
        sys.exit(1)

    APP_ID = sys.argv[1]
    TOKEN = "dify-admin-xxxx"  # подставить
    WS = "your-workspace-id"

    # 1. Get current draft
    draft = get_draft(APP_ID, TOKEN, WS)
    print(f"current hash: {draft['hash']}")
    print(f"nodes: {len(draft['graph']['nodes'])}")
