# Monitoring & Workflow Runs — Верифицировано на Dify 1.14.2

> **Статус**: верифицировано ✅

## Обзор

Dify предоставляет Console API для мониторинга всех запусков workflow и диалогов. Это ключевая возможность для:
- Отладки workflow в production
- Построения dashboards
- Автоматизации алертов на сбои

---

## Workflow Runs (только для mode: workflow)

### Список запусков

```bash
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID/workflow-runs?page=1&limit=10" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

Ответ:
```json
{
  "limit": 10,
  "has_more": false,
  "data": [
    {
      "id": "0cc8cc94-9c4e-4d4f-a87c-b23124aef158",
      "status": "succeeded",
      "elapsed_time": 0.960136,
      "total_tokens": 0,
      "inputs": {"sys.files": [], "sys.user_id": "..."},
      "outputs": {"last_status": "succeeded", "alert_sent": true}
    }
  ]
}
```

> ⚠️ `total` в ответе отсутствует (null). Используйте `/workflow-runs/count` для общего числа.

### Счётчик запусков (верифицировано ✅)

```bash
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID/workflow-runs/count" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

Ответ:
```json
{
  "total": 4,
  "running": 0,
  "succeeded": 4,
  "failed": 0,
  "stopped": 0,
  "partial_succeeded": 0
}
```

### Детали конкретного запуска (верифицировано ✅)

```bash
RUN_ID="0cc8cc94-9c4e-4d4f-a87c-b23124aef158"
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID/workflow-runs/$RUN_ID" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

Поля ответа:
| Поле | Тип | Описание |
|---|---|---|
| `id` | string | UUID запуска |
| `status` | string | `succeeded`, `failed`, `stopped`, `running`, `partial_succeeded` |
| `inputs` | object | Входные данные (включая system vars) |
| `outputs` | object | Выходные данные workflow |
| `elapsed_time` | float | Время выполнения в секундах |
| `total_tokens` | int | Суммарный расход токенов |
| `error` | string/null | Сообщение об ошибке (если failed) |

### Выполнение нод (node-executions) (верифицировано ✅)

Детальный trace каждой ноды в запуске:

```bash
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID/workflow-runs/$RUN_ID/node-executions" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

Ответ (верифицированный пример из Jobs Digest Healthcheck):
```
trigger-schedule [Schedule Trigger] - succeeded (0.000114s)
http-request [Check Last Run] - succeeded (0.033433s)
code [Parse + Alert] - succeeded (0.847494s)
end [End] - succeeded (0.000089s)
```

Структура каждого элемента:
```json
{
  "node_type": "trigger-schedule",
  "title": "Schedule Trigger",
  "status": "succeeded",
  "elapsed_time": 0.000114,
  "inputs": {...},
  "outputs": {...},
  "error": null
}
```

### Экспорт запуска

```bash
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID/workflow-runs/$RUN_ID/export" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

---

## App Export (DSL)

Экспорт всего приложения в YAML DSL:

```bash
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID/export?include_secret=false" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

Ответ: `{"data": "app:\n  name: Jobs Digest Healthcheck\n  mode: workflow\n..."}` — полный YAML DSL для импорта.

---

## Tracing (Langfuse / LangSmith)

Dify поддерживает внешние tracing-провайдеры. Маршруты:

```
GET  /console/api/apps/{app_id}/trace          → статус tracing (enabled, tracing_provider)
POST /console/api/apps/{app_id}/trace-config   → настройка провайдера
GET  /console/api/apps/{app_id}/trace-config?tracing_provider=langfuse → получить config
```

Включение Langfuse:
```bash
curl -sS -X POST "$DIFY_BASE_URL/console/api/apps/$APP_ID/trace-config" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "tracing_provider": "langfuse",
    "tracing_config": {
      "public_key": "pk-lf-...",
      "secret_key": "sk-lf-...",
      "host": "https://cloud.langfuse.com"
    }
  }'
```

Статус (верифицировано):
```bash
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID/trace" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
# → {"enabled": false, "tracing_provider": null}
```

---

## Advanced Chat Workflow Runs (Chatflow)

Для `mode: advanced-chat` (Chatflow) — отдельный endpoint:

```bash
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID/advanced-chat/workflow-runs?page=1&limit=10" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

Счётчик: `GET /console/api/apps/{app_id}/advanced-chat/workflow-runs/count`

---

## Conversations (для chat/agent apps)

```bash
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID/conversations?page=1&limit=20" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

---

## Conversation Variables (только Chatflow)

Консольный API для просмотра conversation variables конкретного chatflow-диалога:

```bash
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID/conversation-variables?conversation_id=CONV_ID" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

> ⚠️ Endpoint `/console/api/apps/{app_id}/conversation-variables` **доступен только для `AppMode.ADVANCED_CHAT`** (Chatflow). Для обычного workflow — 404.

Conversation variables — это переменные, которые персистируют **внутри одной chatflow-сессии**. Управляются нодой `variable-assigner` в DSL. Через Service API можно также обновлять через `PUT /v1/conversations/{conversation_id}/variables`.

---

## Паттерн: мониторинг health workflow

```python
import requests
import time

def check_workflow_health(base_url, app_id, console_token, workspace_id):
    """Проверяет что последний запуск workflow прошёл успешно."""
    headers = {
        "Authorization": f"Bearer {console_token}",
        "X-WORKSPACE-ID": workspace_id,
    }
    
    # Получить последний запуск
    resp = requests.get(
        f"{base_url}/console/api/apps/{app_id}/workflow-runs?page=1&limit=1",
        headers=headers,
    )
    data = resp.json()
    runs = data.get("data", [])
    
    if not runs:
        return {"status": "no_runs", "ok": False}
    
    last_run = runs[0]
    return {
        "run_id": last_run["id"],
        "status": last_run["status"],
        "elapsed": last_run.get("elapsed_time"),
        "ok": last_run["status"] == "succeeded",
    }

result = check_workflow_health(BASE_URL, APP_ID, CONSOLE_TOKEN, WORKSPACE_ID)
print(result)
```
