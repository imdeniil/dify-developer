# Healthcheck Workflow Pattern

Отдельный workflow для мониторинга другого workflow. Полезно когда:
- Workflow запускается по Schedule и работает автономно
- Хочется алёрт в Telegram/email если основной упал
- Не хочется вручную проверять Dify UI каждый день

## Pattern

```
Schedule (час после основного)
  → HTTP GET /console/api/apps/{app_id}/workflow-runs?limit=1
       Headers: Authorization + X-WORKSPACE-ID через env vars
  → Code: parse response, если last run status != succeeded →
         отправить алёрт через httpx в Telegram
  → End
```

⚠️ Ключевые моменты:
1. **URL через контейнер** — `http://api:5001/console/api/...` (не localhost:3006)
2. **Authorization через headers** — не через auth config
3. **Условная отправка через Code node** — не If-Else node (может давать 500)

## Полный пример

### Environment variables (в Settings workflow)

| Name | Type | Value |
|---|---|---|
| `JOBS_DIGEST_APP_ID` | string | `<UUID основного workflow app>` |
| `DIFY_CONSOLE_TOKEN` | secret | `<ADMIN_API_KEY>` |
| `DIFY_WORKSPACE_ID` | string | `<workspace UUID>` |
| `TG_BOT_TOKEN` | secret | `<telegram bot token>` |
| `TG_USER_ID` | string | `<твой user_id в Telegram>` |

### Graph nodes

```python
# Node 1: Schedule Trigger
cron_expression: "0 6 * * *"   # 9:00 МСК = 6:00 UTC (час после основного)

# Node 2: HTTP Request
method: get
url: "http://api:5001/console/api/apps/{{#env.JOBS_DIGEST_APP_ID#}}/workflow-runs?page=1&limit=1"
authorization: { type: "no-auth", config: null }
headers: 'X-WORKSPACE-ID:{{#env.DIFY_WORKSPACE_ID#}}\nAuthorization:Bearer {{#env.DIFY_CONSOLE_TOKEN#}}'

# Node 3: Code (parse + conditional alert)
import json
import httpx

def main(http_body: str, bot_token: str, user_id: str, app_id: str) -> dict:
    try:
        data = json.loads(http_body) if isinstance(http_body, str) else http_body
    except Exception:
        data = {}
    
    runs = data.get("data", []) if isinstance(data, dict) else []
    if not runs:
        last_status = "no_runs"
        error_msg = "No workflow runs found"
        is_failed = True
    else:
        last = runs[0]
        last_status = last.get("status", "unknown")
        error_msg = last.get("error", "") or "(no error)"
        is_failed = last_status not in ("succeeded", "running")
    
    alert_sent = False
    if is_failed:
        text = f"WORKFLOW FAILED\n\nStatus: {last_status}\nError: {error_msg[:300]}\n\nCheck: http://localhost:3006/apps/{app_id}/workflow"
        try:
            r = httpx.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": int(user_id), "disable_web_page_preview": True, "text": text},
                timeout=15
            )
            alert_sent = r.status_code == 200
        except Exception:
            alert_sent = False
    
    return {
        "last_status": last_status,
        "is_failed": is_failed,
        "alert_sent": alert_sent
    }

# Node 4: End
outputs:
  - { variable: last_status, value_selector: [code_node, last_status] }
  - { variable: alert_sent, value_selector: [code_node, alert_sent] }
```

## Расширения pattern

### Multi-workflow monitoring

Если несколько workflows — healthcheck может проверять все в одном Code node:

```python
WORKFLOW_APPS = {
    "jobs_digest": "5af1637b-...",
    "weekly_report": "abc12345-...",
    "data_sync": "def67890-..."
}

def main(jobs_digest_body, weekly_body, sync_body, ...) -> dict:
    alerts = []
    for name, body in [("jobs_digest", jobs_digest_body), ...]:
        # parse each, check status
        if is_failed:
            alerts.append(f"{name}: {error}")
    
    if alerts:
        # send all alerts in one message
        httpx.post(...)
```

### Уровни severity

```python
SEVERITY = {
    "failed": "🔴 CRITICAL",
    "stopped": "🟡 WARNING", 
    "running": "🟢 OK",
    "succeeded": "🟢 OK"
}
```

### Retry основного workflow

Если healthcheck видит failed — можно **триггернуть повторный запуск** через POST /workflows/draft/run:

```python
if is_failed and retry_count < 2:
    httpx.post(
        f"http://api:5001/console/api/apps/{app_id}/workflows/draft/run",
        headers={...},
        json={"inputs": {}, "files": []}
    )
```

## Testing

**Test 1: success case** — основной workflow в succeeded. Healthcheck проходит тихо, `alert_sent: False`.

**Test 2: failure case** — временно форсировать `is_failed = True` в Code node. Проверить что алёрт пришёл в Telegram.

**Test 3: no runs** — удалить все runs через Console API (или новый app). Healthcheck должен сказать `last_status: no_runs`.

## App IDs в нашем окружении

- **Jobs Digest**: `5af1637b-c5fc-4eb7-b985-7fd2cf7f1a4d`
- **Jobs Digest Healthcheck**: `cee9986e-96f9-41ea-920b-7722eb185b8a`
