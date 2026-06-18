# Console API Endpoints для Workflow разработки

Все пути относительно `$DIFY_BASE_URL` (для нас: `http://localhost:3006`).
Все запросы требуют:
- `Authorization: Bearer ${DIFY_CONSOLE_TOKEN}`
- `X-WORKSPACE-ID: ${DIFY_WORKSPACE_ID}` (критично!)

## Справочник endpoints

### Создание/импорт приложений

| Method | Endpoint | Назначение |
|---|---|---|
| POST | `/console/api/apps` | Создать app (chat/workflow/agent и т.д.) |
| GET | `/console/api/apps` | Список apps в workspace |
| GET | `/console/api/apps/{app_id}` | Получить app |
| DELETE | `/console/api/apps/{app_id}` | Удалить app |
| **POST** | **`/console/api/apps/imports`** | **Импорт app из YAML DSL** (рекомендуемый способ) |
| GET | `/console/api/apps/{app_id}/export` | Экспорт app в DSL |
| POST | `/console/api/apps/imports/{import_id}/confirm` | Подтвердить импорт (если PENDING) |
| GET | `/console/api/apps/imports/{app_id}/check-dependencies` | Проверить зависимости (модели, datasets, MCP) |

### Workflow draft (главное для разработки)

| Method | Endpoint | Назначение |
|---|---|---|
| **GET** | **`/console/api/apps/{app_id}/workflows/draft`** | Получить текущий draft graph |
| **POST** | **`/console/api/apps/{app_id}/workflows/draft`** | **Sync (обновить) draft graph** |
| POST | `/console/api/apps/{app_id}/workflows/draft/run` | Запустить draft (для теста) — SSE поток событий |
| POST | `/console/api/apps/{app_id}/workflows/draft/iteration/nodes/{node_id}/run` | Запустить iteration node отдельно |
| GET/POST/DELETE | `/console/api/apps/{app_id}/workflows/draft/variables` | Environment/conversation/system variables |

### Опубликованный workflow

| Method | Endpoint | Назначение |
|---|---|---|
| POST | `/console/api/apps/{app_id}/workflows/publish` | Опубликовать текущий draft |
| GET | `/console/api/apps/{app_id}/workflows/published` | Получить опубликованный |

### Workflow runs (тестирование/мониторинг)

| Method | Endpoint | Назначение |
|---|---|---|
| GET | `/console/api/apps/{app_id}/workflow-runs` | Список запусков |
| GET | `/console/api/apps/{app_id}/workflow-runs/{run_id}` | Детали конкретного запуска |
| POST | `/console/api/apps/{app_id}/workflow-runs/{run_id}/stop` | Остановить execution |

### App API Keys (для Service API)

| Method | Endpoint | Назначение |
|---|---|---|
| GET | `/console/api/apps/{app_id}/api-keys` | Список ключей |
| **POST** | **`/console/api/apps/{app_id}/api-keys`** | Создать ключ (для запуска через /v1/) |
| DELETE | `/console/api/apps/{app_id}/api-keys/{api_key_id}` | Удалить ключ |

### Tool providers (включая MCP)

| Method | Endpoint | Назначение |
|---|---|---|
| GET | `/console/api/workspaces/current/tool-providers` | Все tool providers |
| **POST** | **`/console/api/workspaces/current/tool-provider/mcp`** | **Создать MCP provider** |
| PUT | `/console/api/workspaces/current/tool-provider/mcp` | Обновить |
| DELETE | `/console/api/workspaces/current/tool-provider/mcp` | Удалить |

### Model providers

| Method | Endpoint | Назначение |
|---|---|---|
| GET | `/console/api/workspaces/current/model-providers` | Все model providers |
| POST | `/console/api/workspaces/current/model-providers/{provider}/credentials` | Сохранить credentials |
| POST | `/console/api/workspaces/current/model-providers/{provider}/credentials/validate` | Validate |
| GET | `/console/api/workspaces/current/model-providers/{provider}/models` | Список моделей провайдера |
| POST | `/console/api/workspaces/current/default-model` | Установить default model |

### Default workflow block configs (полезно для node schemas)

| Method | Endpoint | Назначение |
|---|---|---|
| GET | `/console/api/apps/{app_id}/workflows/default-workflow-block-configs` | Все default configs для всех node types |
| GET | `/console/api/apps/{app_id}/workflows/default-workflow-block-configs/{block_type}` | Default config для конкретного типа |

## Common patterns

### Создать новый workflow (рекомендуемый flow)

```python
# 1. Создать пустой app через DSL импорт
POST /console/api/apps/imports
{
  "mode": "yaml-content",
  "yaml_content": "<minimal DSL>",
  "name": "My Workflow",
  "icon_type": "emoji",
  "icon": "🚀"
}
# → {app_id, status: completed}

# 2. Обновлять graph инкрементально
POST /console/api/apps/{app_id}/workflows/draft
{graph, features, hash, environment_variables, conversation_variables}

# 3. Тестировать через draft run
POST /console/api/apps/{app_id}/workflows/draft/run
{inputs: {}, files: []}
# → SSE поток с node_finished/node_failed/workflow_finished events

# 4. Опубликовать
POST /console/api/apps/{app_id}/workflows/publish
```

### Обновить существующий graph (важно!)

```python
# 1. GET draft → берём hash
GET /console/api/apps/{app_id}/workflows/draft
# → {graph, hash, environment_variables, ...}

# 2. Меняем graph (добавляем nodes/edges)

# 3. POST с тем же hash (optimistic locking)
POST /console/api/apps/{app_id}/workflows/draft
{graph, features, hash: <from step 1>, environment_variables, conversation_variables}
# → {result: success, hash: <new_hash>}
```

⚠️ **Hash обязателен.** Без него → `DraftWorkflowNotSync` ошибка.

### Парсинг SSE ответа

Draft run возвращает Server-Sent Events. Пример парсинга:

```python
import json
raw = response_text  # полный ответ curl
events = []
for line in raw.split('\n'):
    if line.startswith('data: '):
        try:
            events.append(json.loads(line[6:]))
        except: pass

for e in events:
    ev_type = e.get('event')
    data = e.get('data', {})
    if ev_type == 'node_finished':
        node_id = data.get('node_id')
        status = data.get('status')  # succeeded | failed
        outputs = data.get('outputs', {})
        elapsed = data.get('elapsed_time', 0)
        error = data.get('error')
    elif ev_type == 'workflow_finished':
        status = data.get('status')
```

## Quick reference для common tasks

| Что хочу | Endpoint |
|---|---|
| Создать workflow с шаблоном | POST `/apps/imports` с YAML DSL |
| Добавить node в существующий | GET draft → modify graph → POST draft |
| Протестировать workflow | POST `/apps/{id}/workflows/draft/run` |
| Получить ключ для /v1/ вызова | POST `/apps/{id}/api-keys` |
| Подключить MCP сервер | POST `/workspaces/current/tool-provider/mcp` |
| Узнать schema конкретного node type | GET `/apps/{id}/workflows/default-workflow-block-configs/{type}` |
