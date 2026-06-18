# App Management — Верифицировано на Dify 1.14.2

> **Статус**: верифицировано ✅

## App Lifecycle через Console API

### Создание приложения

```bash
curl -sS -X POST "$DIFY_BASE_URL/console/api/apps" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My App",
    "mode": "workflow",
    "icon_type": "emoji",
    "icon": "🚀",
    "icon_background": "#FFEAD5"
  }'
```

Доступные `mode`:
| mode | Тип приложения |
|---|---|
| `chat` | Chatbot |
| `agent-chat` | Agent |
| `workflow` | Workflow |
| `advanced-chat` | Chatflow |
| `completion` | Text Generator |

### Список приложений

```bash
curl -sS "$DIFY_BASE_URL/console/api/apps?page=1&limit=30" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

Query params: `page`, `limit`, `mode` (фильтр по типу), `name` (поиск по имени).

### Получение деталей app

```bash
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

### Удаление

```bash
curl -sS -X DELETE "$DIFY_BASE_URL/console/api/apps/$APP_ID" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
# → HTTP 204
```

### Копирование (дублирование)

```bash
curl -sS -X POST "$DIFY_BASE_URL/console/api/apps/$APP_ID/copy" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{"name": "My App (Copy)", "icon_type": "emoji", "icon": "📋"}'
```

### Экспорт в DSL YAML (верифицировано ✅)

```bash
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID/export?include_secret=false" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
# → {"data": "app:\n  name: ...\n  mode: workflow\n  ..."}
```

`include_secret=true` включает credentials в DSL (осторожно!).

### Переименование

```bash
curl -sS -X POST "$DIFY_BASE_URL/console/api/apps/$APP_ID/name" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{"name": "New App Name"}'
```

### Изменение иконки

```bash
curl -sS -X POST "$DIFY_BASE_URL/console/api/apps/$APP_ID/icon" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{"icon_type": "emoji", "icon": "🤖", "icon_background": "#E0F2FE"}'
```

---

## API Keys

### Создание App API Key

```bash
curl -sS -X POST "$DIFY_BASE_URL/console/api/apps/$APP_ID/api-keys" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "Content-Type: application/json"
```

Ответ:
```json
{"id": "...", "token": "app-xxxxxxxxxxxxxxxxxx", "last_used_at": null, "created_at": 1781761234}
```

### Список ключей

```bash
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID/api-keys" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

### Dataset API Key

```bash
# Создать
curl -sS -X POST "$DIFY_BASE_URL/console/api/datasets/api-keys" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "Content-Type: application/json"

# Список
curl -sS "$DIFY_BASE_URL/console/api/datasets/api-keys" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

---

## Publish / Site Settings

### Включить/выключить Web публикацию (site)

```bash
curl -sS -X POST "$DIFY_BASE_URL/console/api/apps/$APP_ID/site-enable" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{"enable_site": true}'
```

### Включить/выключить API доступ

```bash
curl -sS -X POST "$DIFY_BASE_URL/console/api/apps/$APP_ID/api-enable" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{"enable_api": true}'
```

---

## Workflow Publish (draft → published)

Публикация черновика workflow:

```bash
curl -sS -X POST "$DIFY_BASE_URL/console/api/apps/$APP_ID/workflows/publish" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "Content-Type: application/json"
```

После публикации workflow доступен через Service API `/v1/workflows/run`.

---

## Паттерн: полный деплой нового workflow

```python
import requests
import yaml

BASE_URL = "http://localhost:3006"
CONSOLE_TOKEN = "dify-admin-..."
WORKSPACE_ID = "..."

headers = {
    "Authorization": f"Bearer {CONSOLE_TOKEN}",
    "X-WORKSPACE-ID": WORKSPACE_ID,
}

# 1. Создать app
app = requests.post(f"{BASE_URL}/console/api/apps", headers=headers, json={
    "name": "My Workflow",
    "mode": "workflow",
    "icon_type": "emoji",
    "icon": "⚙️",
}).json()
APP_ID = app["id"]

# 2. Синхронизировать DSL
# 2а. Получить текущий draft и его hash (оптимистичная блокировка)
draft = requests.get(f"{BASE_URL}/console/api/apps/{APP_ID}/workflows/draft", headers=headers).json()
current_hash = draft.get("hash")

with open("workflow.yaml") as f:
    dsl_data = yaml.safe_load(f)

# 2б. Отправить POST c хешем и всеми переменными (чтобы избежать сброса)
requests.post(
    f"{BASE_URL}/console/api/apps/{APP_ID}/workflows/draft",
    headers=headers,
    json={
        "graph": dsl_data["workflow"]["graph"],
        "features": dsl_data["workflow"]["features"],
        "hash": current_hash,
        "environment_variables": dsl_data["workflow"].get("environment_variables", []),
        "conversation_variables": dsl_data["workflow"].get("conversation_variables", [])
    },
)

# 3. Опубликовать
requests.post(f"{BASE_URL}/console/api/apps/{APP_ID}/workflows/publish", headers=headers)

# 4. Создать API key
key_resp = requests.post(f"{BASE_URL}/console/api/apps/{APP_ID}/api-keys", headers=headers).json()
APP_KEY = key_resp["token"]

print(f"Deployed: {APP_ID}")
print(f"API Key: {APP_KEY}")
print(f"Run: curl -X POST {BASE_URL}/v1/workflows/run -H 'Authorization: Bearer {APP_KEY}' ...")
```
