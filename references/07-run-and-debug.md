# Run и Debug Workflow

## Запуск draft workflow

```bash
POST /console/api/apps/{app_id}/workflows/draft/run
Headers: Authorization, X-WORKSPACE-ID
Body: { "inputs": {}, "files": [] }
```

Response: **Server-Sent Events (SSE)** поток.

## Парсинг SSE

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
    ev = e.get('event')
    data = e.get('data', {})
    
    if ev == 'workflow_started':
        run_id = data.get('id')
        print(f'Workflow started: {run_id}')
    
    elif ev == 'node_started':
        node_id = data.get('node_id')
        print(f'  → Started: {node_id}')
    
    elif ev == 'node_finished':
        node_id = data.get('node_id')
        title = data.get('title')
        status = data.get('status')           # succeeded | failed
        elapsed = data.get('elapsed_time', 0)
        outputs = data.get('outputs', {})
        error = data.get('error')
        
        if status == 'failed':
            print(f'  ✗ {node_id} "{title}" FAILED: {error}')
        else:
            print(f'  ✓ {node_id} "{title}" {elapsed:.1f}s')
            for k, v in outputs.items():
                print(f'      {k}: {json.dumps(v, ensure_ascii=False)[:200]}')
    
    elif ev == 'workflow_finished':
        status = data.get('status')
        outputs = data.get('outputs')
        elapsed = data.get('elapsed_time')
        print(f'\n=== WORKFLOW {status} ({elapsed:.1f}s) ===')
        print(f'Outputs: {outputs}')
    
    elif ev == 'text_chunk':
        # streaming text output (для LLM nodes)
        chunk = data.get('text', '')
        # можно накапливать
    
    elif ev in ('workflow_failed', 'error'):
        msg = data.get('error') or data.get('message')
        print(f'✗ ERROR: {msg}')
```

## Типичный ответ workflow run

```
event: ping

data: {"event":"workflow_started", "data": {...}}

data: {"event":"node_started", "data": {"node_id": "...", "title": "..."}}

data: {"event":"node_finished", "data": {"node_id": "...", "status": "succeeded", "outputs": {...}}}

... повторяется для каждого node ...

data: {"event":"workflow_finished", "data": {"status": "succeeded", "outputs": {...}}}
```

## Структуры данных в events

### workflow_started
```python
{
  "event": "workflow_started",
  "workflow_run_id": "uuid",
  "task_id": "uuid",
  "data": {
    "id": "uuid",
    "workflow_id": "uuid",
    "inputs": {"sys.files": [], "sys.user_id": "...", ...},
    "created_at": 1781650079,
    "reason": "initial"
  }
}
```

### node_finished
```python
{
  "event": "node_finished",
  "workflow_run_id": "uuid",
  "task_id": "uuid",
  "data": {
    "id": "execution_uuid",
    "node_id": "1749000000050",
    "node_type": "llm",
    "title": "LLM Classifier",
    "index": 1,                          # порядковый номер в execution
    "predecessor_node_id": "1749000000040",
    "inputs": {...},                     # что получил на вход
    "inputs_truncated": false,
    "process_data": {},
    "outputs": {...},                    # что вернул
    "outputs_truncated": false,
    "status": "succeeded",               # succeeded | failed
    "error": null,                       # или string если failed
    "elapsed_time": 21.04,
    "execution_metadata": {
      "total_tokens": 1469,
      "total_price": "0",
      "currency": "RMB",
      "latency": 21.04,
      "prompt_tokens": ...,
      "completion_tokens": ...
    },
    "created_at": 1781651758,
    "finished_at": 1781651779
  }
}
```

### node_failed / workflow_failed
```python
{
  "event": "node_failed",
  "data": {
    "node_id": "...",
    "status": "failed",
    "error": "PluginInvokeError: {\"args\":..., \"message\":...}"
  }
}
```

### text_chunk (streaming)
```python
{
  "event": "text_chunk",
  "data": {
    "text": "chunk of LLM output",
    "from_variable_selector": ["1749000000050", "text"]
  }
}
```

## Дебаг типичных ошибок

### `invalid_param` (HTTP 400)

```
1 validation error for ToolNodeData
tool_parameters.entities.type
  Value error, value must be a string
```

→ Проверь schema node. Часто type или поле не подходит.

### `PluginInvokeError`

```
[models] Error: Messages.create() got an unexpected keyword argument 'response_format'
```

→ См. [06-llm-node-gotchas.md](06-llm-node-gotchas.md).

### `ToolProviderNotFoundError`

```
mcp provider <id> not found
```

→ `provider_id` должен быть **server_identifier**, не UUID. См. [05-mcp-tool-node.md](05-mcp-tool-node.md).

### `DraftWorkflowNotSync`

```
hash mismatch
```

→ Перед POST /workflows/draft всегда делать GET чтобы получить актуальный hash.

### Node failed without specific error

Глянь `api` container logs:
```bash
docker logs docker-api-1 --tail=50 2>&1 | grep -iE "error|mcp|tool|llm"
```

## Live monitoring через logs

```bash
# Все HTTP запросы к Console API
docker logs -f docker-nginx-1 2>&1 | grep -i "console/api"

# Backend errors
docker logs -f docker-api-1 2>&1 | grep -iE "error|exception|traceback"

# MCP plugin invocation errors
docker logs -f docker-plugin_daemon-1 2>&1 | grep -iE "error|tool|mcp"

# Workflow execution в real-time
docker logs -f docker-api-1 2>&1 | grep -iE "workflow_run|node_finished"
```

## Дебаг workflow runs (после выполнения)

```bash
# Список всех запусков
GET /console/api/apps/{app_id}/workflow-runs?page=1&limit=20

# Детали конкретного запуска (включая все node outputs)
GET /console/api/apps/{app_id}/workflow-runs/{run_id}
```

UI Dify (http://localhost:3006) → открыть app → "View Runs" — визуальный graph с outputs каждой node.

## Testing patterns

### Изолированный тест одной node

Создать mini-workflow только для тестирования:

```yaml
# mini-test.yml
app:
  name: Test LLM Node
  mode: workflow
workflow:
  graph:
    nodes:
      - id: 'start_node'
        data: { type: start, title: Start, variables: [] }
      - id: 'llm_test'
        data: { type: llm, title: LLM, ... }
      - id: 'end_node'
        data: { type: end, title: End, outputs: [{ variable: result, value_selector: ['llm_test', 'text'] }] }
    edges: [...]
```

Импортнуть, запустить, посмотреть outputs LLM. Удалить.

### Тестирование MCP tool

Аналогично — mini-workflow с MCP node, проверить output format.

### Snapshot testing

Сохранить outputs после успешного run в файл, сравнивать с следующими запусками:

```python
import json
with open(f'snapshots/{test_name}.json', 'w') as f:
    json.dump(outputs, f, indent=2, ensure_ascii=False)
```

## Quick smoke test template

Минимальный workflow для проверки что **всё** работает:

```yaml
Schedule → Code → MCP → LLM → HTTP → End
```

Если все 5 nodes succeeded → Console API, MCP, LLM, HTTP, env vars — всё корректно настроено.
