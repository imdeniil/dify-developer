# Справочник Node Types

Все типы nodes в Dify workflow + их `data` schema. Schema извлечена через `default-workflow-block-configs` endpoint и проверена на практике.

## Как получить default config для любого типа

```bash
GET /console/api/apps/{app_id}/workflows/default-workflow-block-configs/{block_type}
```

## Полный список типов

### trigger-schedule — Schedule Trigger

**Start node для workflow по расписанию. Подробное руководство по триггерам см. в [trigger.md](file:///home/keemor/defyproj/dify-workflow-dev/nodes/trigger.md).**

```yaml
data:
  title: Schedule Trigger
  type: trigger-schedule
  mode: cron                   # cron | visual
  cron_expression: '0 5 * * *' # только при mode=cron
  frequency: daily             # только при mode=visual
  timezone: UTC
  visual_config:               # только при mode=visual
    monthly_days: [1]
    on_minute: 0
    time: '8:00 AM'
    weekdays: [sun]
```

**Outputs**: `sys.files`, `sys.user_id`, `sys.app_id`, `sys.timestamp`, `sys.workflow_id`, `sys.workflow_run_id`

⚠️ **Cron в UTC!** 8:00 МСК = `0 5 * * *`.

### webhook — Webhook Trigger

**Start node для запуска по HTTP webhook. Подробное руководство по триггерам см. в [trigger.md](file:///home/keemor/defyproj/dify-workflow-dev/nodes/trigger.md).**

```yaml
data:
  title: Webhook
  type: webhook
  method: get                  # get | post
  content_type: application/json
  headers: []
  params: []
  body: []
  async_mode: true
  status_code: 200
  response_body: ''
  timeout: 30
```

### start — User Input (для workflow с ручным запуском)

**Подробное руководство см. в [start.md](file:///home/keemor/defyproj/dify-workflow-dev/nodes/start.md).**

```yaml
data:
  title: User Input
  type: start
  variables:
    - default: ''
      hint: ''
      label: User query
      options: []
      placeholder: ''
      required: true
      type: text-input         # text-input | paragraph | number | select | file
      variable: query
```

### end — End (финальный output)

**Подробное руководство см. в [end.md](file:///home/keemor/defyproj/dify-workflow-dev/nodes/end.md).**

```yaml
data:
  title: End
  type: end
  outputs:
    - variable: result
      value_selector: ['<node_id>', '<output_var>']
```

`value_selector` — array: `['node_id', 'variable_name']`.

### code — Code (Python/JS)

```yaml
data:
  title: My Code
  type: code
  variables:                   # входные параметры
    - variable: input1
      value_selector: ['<source_node_id>', '<output_var>']
    - variable: input2
      value_selector: ['<other_node>', 'something']
    - variable: env_var
      value_selector: ['env', 'SECRET_VAR']   # доступ к environment variables
  code_language: python3       # python3 | javascript
  code: |
    def main(input1: str, input2: list, env_var: str) -> dict:
        return {
            "result": input1 + str(input2),
            "count": len(input2) if isinstance(input2, list) else 0,
        }
  outputs:                     # декларация выходов (ВАЖНО для типизации)
    result: { type: string, children: null }
    count: { type: number, children: null }
    items: { type: 'array[object]', children: null }
```

**Output types**: `string`, `number`, `boolean`, `object`, `array[object]`, `array[string]`, `array[number]`.

⚠️ Python 3.12 (в plugin_daemon). Доступны стандартные библиотеки + `json`, `datetime`. Без pip packages.

**Sandbox features:**
- `httpx` доступен — можно делать HTTP calls прямо из Python (без отдельных HTTP Request node)
- `json`, `re`, `datetime` — стандартные
- Environment variables через `value_selector: ['env', 'VAR_NAME']` — передаются как function args

**Pattern: Code node с side-effects (замена If-Else + HTTP Request):**
```python
import httpx

def main(input_data, should_alert, bot_token, user_id) -> dict:
    if should_alert:
        httpx.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": int(user_id), "text": "Alert"},
            timeout=15
        )
    return {"done": True}
```

Заменяет: If-Else node + HTTP Request node (о правильном синтаксисе сравнений в If-Else см. [08-gotchas-and-lessons.md](08-gotchas-and-lessons.md) #13).

⚠️ **Array outputs limit (Первоначальное утверждение: 30 элементов)**: **❌ ОПРОВЕРГНУТО**. Тесты подтвердили, что лимита в 30 элементов для Code Node нет (успешно протестировано до 500 элементов). См. подробнее в [code.md](nodes/code.md).

### llm — LLM (генерация текста)

```yaml
data:
  title: LLM Node
  type: llm
  model:
    provider: imdeniil/zai-coding-plan/zai_coding_plan   # provider_id
    name: glm-4.7-flash                                    # model name
    mode: chat                                             # chat | completion
    completion_params:
      temperature: 0.5
      max_tokens: 4096
      # ⚠️ НЕ ставьте response_format для Anthropic-совместимых моделей!
  prompt_template:
    - role: system
      text: 'You are a helpful assistant.'
      edition_type: basic      # basic | jitter
    - role: user
      text: 'Process: {{#<source_node_id>.<variable>#}}'
      edition_type: basic
  vision:
    enabled: false
    configs: { variable_selector: [] }
  memory:
    enabled: false
    window: { enabled: false, size: 50 }
  context:
    enabled: false
    variable_selector: []
  structured_output_enabled: false   # см. 06-llm-node-gotchas.md
  structured_output:                 # только если enabled: true
    schema: { ... JSON schema ... }
  retry_config:
    enabled: false
    max_retries: 1
    retry_interval: 1000
    exponential_backoff: { enabled: false, multiplier: 2, max_interval: 10000 }
```

**Outputs**: `text` (основной), `reasoning_content` (для reasoning моделей), `usage` (token stats).

См. [06-llm-node-gotchas.md](06-llm-node-gotchas.md) для нюансов.

### tool — Tool node (MCP / plugin tools)

**Подробное руководство см. в [tool.md](file:///home/keemor/defyproj/dify-workflow-dev/nodes/tool.md).**

```yaml
data:
  title: MCP Tool
  type: tool
  provider_id: '<server_identifier>'   # для MCP — server_identifier, НЕ UUID!
  provider_type: mcp                   # mcp | builtin | api | workflow
  provider_name: 'Telegram (MCP)'
  tool_name: export_messages
  tool_label: export_messages
  tool_parameters:                     # см. 05-mcp-tool-node.md
    entities:
      type: variable                   # variable | constant | mixed
      value: ['<code_node_id>', 'entities']
    start_date:
      type: variable
      value: ['<date_node_id>', 'start_date']
    some_static:
      type: constant
      value: 'fixed-value'
  tool_configurations: {}
  plugin_id: ''
```

⚠️ См. [05-mcp-tool-node.md](05-mcp-tool-node.md) — критичные грабли с array параметрами.

### http-request — HTTP Request

```yaml
data:
  title: Send to Telegram
  type: http-request
  method: post                          # get | post | put | delete | patch | head
  url: 'https://api.telegram.org/bot{{#env.BOT_TOKEN#}}/sendMessage'
  authorization:
    type: no-auth                       # no-auth | api-key | bearer | etc
    config: null
  headers: 'Content-Type:application/json'  # string с переводами строк
  params: ''                            # query params как string
  body:
    type: json                          # none | form-data | x-www-form-urlencoded | json | raw
    data: '{"chat_id": "{{#env.USER_ID#}}", "text": "{{#<prev_node>.text#}}"}'
  variables: []
  timeout:
    connect: 10
    read: 60
    write: 60
    max_connect_timeout: 10
    max_read_timeout: 60
    max_write_timeout: 60
  ssl_verify: true
```

**Outputs**: `status_code`, `body`, `headers`, `files`.

⚠️ **URL для HTTP Request к самому Dify** — использовать внутренний docker network:
- ✅ `http://api:5001/console/api/...` (Dify API контейнер)
- ✅ `http://nginx:3006/...` (через nginx)
- ❌ `http://localhost:3006/...` — не работает из workflow (plugin_daemon не видит host)

⚠️ **Authorization через headers, не через auth config** — variable substitution в `authorization.config` хрупкая:
```yaml
# ❌ может подвисать
authorization: { type: bearer, config: { token: "{{#env.TOKEN#}}" } }

# ✅ надёжно
headers: 'Authorization:Bearer {{#env.TOKEN#}}'
authorization: { type: no-auth, config: null }
```

⚠️ **Для условных HTTP requests** — проще через Code node с httpx:
```python
import httpx
def main(should_send, ...) -> dict:
    if should_send:
        httpx.post(...)
    return {"done": True}
```
Заменяет If-Else + HTTP Request combo (о правильных операторах сравнения в If-Else см. [08-gotchas-and-lessons.md](08-gotchas-and-lessons.md) #13).

### iteration — Iteration (цикл по массиву)

```yaml
data:
  title: Process Items
  type: iteration
  iterator_selector: ['<source_node_id>', 'items']   # array source
  iterator_input_type: array[string]                  # type of elements
  output_selector: ['<inner_last_node_id>', 'field']  # what to collect from each iter
  output_type: array[string]                          # type of collected output
  is_parallel: false
  parallel_nums: 10
  error_handle_mode: terminated      # terminated | continue-on-error | remove-abnormal-output
  flatten_output: false              # true = flatten nested arrays
  start_node_id: '<iteration_start_node_id>'
height: 178
id: <iteration_node_id>
parentId: null                        # iteration node — top-level
position: {x: 680, y: 282}
zIndex: 1
```

**Iteration — это контейнер.** Внутри него другие nodes. Полная структура:

```yaml
# 1. Iteration start node (обязательный, inside iteration)
- data:
    title: ''
    type: iteration-start
    isInIteration: true
  id: <iteration_start_id>           # = iteration.start_node_id
  parentId: <iteration_node_id>      # ссылка на parent
  type: custom-iteration-start       # специальный type
  zIndex: 1002

# 2. Inner nodes (внутри iteration)
- data:
    title: Inner Node
    type: code                        # или llm / tool / http-request
    isInIteration: true
    isInLoop: false
    iteration_id: <iteration_node_id> # ссылка на parent
    variables:
      # Текущий элемент итерации — доступ через iteration_node.item:
      - variable: item
        value_selector: [<iteration_node_id>, item]
        value_type: string            # type of iterator elements
  id: <inner_node_id>
  parentId: <iteration_node_id>
  zIndex: 1002
```

**Edges (важно отличать inner vs outer):**

```yaml
# INNER edge (внутри iteration):
- data:
    isInIteration: true
    isInLoop: false
    iteration_id: <iteration_node_id>
    sourceType: iteration-start       # или code/llm/tool
    targetType: code
  source: <source_id>
  target: <target_id>
  zIndex: 1002                        # inner edges — высокий zIndex

# OUTER edge (снаружи iteration):
- data:
    isInIteration: false
    isInLoop: false
    sourceType: custom                # или iteration
    targetType: iteration             # или custom
  source: <source_id>
  target: <target_id>
  zIndex: 0                           # outer edges — zIndex 0
```

**Доступ к переменным снаружи:** inner nodes могут ссылаться на outputs nodes за пределами iteration через обычный `value_selector: ['<outer_node_id>', 'field']`.

**Output iteration:** после completion, iteration node экспонирует `output` (array). Доступ через `value_selector: ['<iteration_node_id>', 'output']`.

⚠️ **Array of arrays не поддерживается** в Dify outputs. Если нужно итерировать массив массивов — обход через **JSON strings**:
```python
# Code node возвращает array[string] где каждый string — JSON-сериализованный массив
import json
def main(big_array: list) -> dict:
    chunks = [big_array[i:i+17] for i in range(0, len(big_array), 17)]
    return {"chunks": [json.dumps(c) for c in chunks]}  # array[string]
```
Внутри iteration — Code node парсит JSON обратно в array.

Iteration — это **контейнер**. Внутри него другие nodes. Они имеют parent `iteration_id`.

### if-else — Conditional Branch

```yaml
data:
  title: If-Else
  type: if-else
  cases:
    - case_id: 'true_case'
      logical_operator: and      # and | or
      conditions:
        - comparison_operator: contains  # contains | = | ≠ | > | < | ≥ | ≤ | is | is not | null | not null
          value: 'search_term'
          variable_selector: ['<node>', '<var>']
          varType: string
```

### question-classifier — Question Classifier

LLM-классификация ввода по классам.

```yaml
data:
  title: Classifier
  type: question-classifier
  query_variable_selector: ['start', 'query']
  model: { provider, name, mode, completion_params }
  classes:
    - id: 'class-1'
      name: 'Tech question'
    - id: 'class-2'
      name: 'Sales'
  instruction: 'Classify user query'
```

### template-transform — Jinja2 Template

```yaml
data:
  title: Format
  type: template-transform
  variables:
    - variable: arg1
      value_selector: ['<node>', 'var']
  template: '{{ arg1 }} processed'
```

### variable-aggregator — Variable Aggregator

Схождение параллельных веток.

```yaml
data:
  title: Aggregate
  type: variable-aggregator
  variables:
    - ['<node1>', 'output']
    - ['<node2>', 'output']
  output_type: string
```

### variable-assigner — Conversation Variable Setter (только chatflow или внутри Loop)

Для записи/обновления в conversation variables или loop variables. Подробное руководство см. в [variable-assigner.md](file:///home/keemor/defyproj/dify-workflow-dev/nodes/variable-assigner.md). См. также [loop.md](file:///home/keemor/defyproj/dify-workflow-dev/nodes/loop.md).

### knowledge-retrieval — Knowledge Base Search

**Подробное руководство см. в [knowledge-retrieval.md](file:///home/keemor/defyproj/dify-workflow-dev/nodes/knowledge-retrieval.md).**

```yaml
data:
  title: RAG
  type: knowledge-retrieval
  query_variable_selector: ['start', 'query']
  dataset_ids: ['<dataset_uuid>']
  retrieval_mode: multiple   # single | multiple
  multiple_retrieval_config:
    top_k: 3
    score_threshold_enabled: false
    score_threshold: 0.5
    reranking_enable: false
```

### parameter-extractor — Parameter Extractor

LLM-извлечение structured данных (function calling).

```yaml
data:
  title: Extract Params
  type: parameter-extractor
  model: { provider, name, mode, completion_params }
  parameters:
    - name: entity
      type: string
      description: 'Target entity'
      required: true
  query: '{{#start.query#}}'
  instruction: ''
  inference_mode: function_call    # function_call | prompt
```

### agent — Agent Node (внутри workflow)

**Подробное руководство см. в [agent.md](file:///home/keemor/defyproj/dify-workflow-dev/nodes/agent.md).**

```yaml
data:
  title: Agent
  type: agent
  agent_strategy:
    provider: 'agent_strategy_provider'
    strategy_name: 'react'
    strategy_inputs: { ... }
  model: { provider, name, mode, completion_params }
  tools: ['tool_node_id_1', 'tool_node_id_2']
  query: '{{#start.query#}}'
```

### answer — Answer (для chatflow)

Финальный текстовый ответ в чат. Подробное руководство см. в [answer.md](file:///home/keemor/defyproj/dify-workflow-dev/nodes/answer.md).

### document-extractor — Document Extractor

Извлечение текста из загруженных документов. См. подробное руководство в [document-extractor.md](file:///home/keemor/defyproj/dify-workflow-dev/nodes/document-extractor.md).

### list-operator — List Operator

Фильтрация, сортировка, ограничение длины и извлечение элемента по индексу для массивов. См. подробное руководство в [list-operator.md](file:///home/keemor/defyproj/dify-workflow-dev/nodes/list-operator.md).

### loop — Loop (цикл с переменными)

Циклическое выполнение шагов с изменяемыми переменными и условиями выхода. См. подробное руководство в [loop.md](file:///home/keemor/defyproj/dify-workflow-dev/nodes/loop.md).

### human-input — Human Input

Пауза workflow для ручного ввода или ревью человеком (HITL). См. подробное руководство в [human-input.md](file:///home/keemor/defyproj/dify-workflow-dev/nodes/human-input.md).

## Сравнение рабочих примеров

См. [examples/](examples/) — там лежат готовые шаблоны для часто нужных node types.

