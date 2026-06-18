# YAML DSL формат для Dify apps

Используется в `POST /console/api/apps/imports` для создания приложений.

## Структура верхнего уровня

```yaml
app:
  description: 'My workflow'
  icon: 🚀                    # emoji или URL на иконку
  icon_background: '#FFEAD5'
  icon_type: emoji            # emoji | image
  mode: workflow              # workflow | advanced-chat | chat | agent-chat | completion
  name: My Workflow
  use_icon_as_answer_icon: false
dependencies: []              # plugin IDs если нужны
kind: app
version: 0.6.0                # версия DSL

workflow:
  conversation_variables: []  # для chatflow
  environment_variables: []   # см. 04-variable-templating.md
  features:                   # настройки приложения
    file_upload:
      enabled: false
      ...
    opening_statement: ''
    retriever_resource: { enabled: false }
    sensitive_word_avoidance: { enabled: false }
    speech_to_text: { enabled: false }
    suggested_questions: []
    suggested_questions_after_answer: { enabled: false }
    text_to_speech: { enabled: false, language: '', voice: '' }
  graph:
    edges: [...]              # связи между nodes
    nodes: [...]              # массив node объектов
    viewport: { x: 0, y: 0, zoom: 1 }
  rag_pipeline_variables: []
```

## Node объект (общая структура)

```yaml
- data:                       # тип-специфичные данные
    title: Node Title
    type: <node_type>         # см. 03-node-types.md
    # ... тип-специфичные поля
  height: 89                  # визуальный размер (можно default)
  id: '<unique_string_id>'    # уникальный ID (часто timestamp как string)
  position: { x: 80, y: 282 }
  positionAbsolute: { x: 80, y: 282 }  # обычно = position
  sourcePosition: right
  targetPosition: left
  type: custom                # всегда 'custom'
  width: 242
```

⚠️ **ID nodes** — строка, обычно timestamp-based (`1749000000010`). Уникально в рамках graph.

## Edge объект

```yaml
- data:
    isInIteration: false      # true если edge внутри iteration
    isInLoop: false
    sourceType: custom        # всегда 'custom' (или специфичный тип)
    targetType: custom
  id: '<source_id>-source-<target_id>-target'   # конвенция именования
  source: '<source_node_id>'
  sourceHandle: source        # всегда 'source'
  target: '<target_node_id>'
  targetHandle: target        # всегда 'target'
  type: custom
  zIndex: 0
```

## Schedule Trigger example (минимальный workflow)

```yaml
app:
  description: ''
  icon: 💼
  icon_background: '#000000'
  icon_type: emoji
  mode: workflow
  name: My Workflow
  use_icon_as_answer_icon: false
dependencies: []
kind: app
version: 0.6.0
workflow:
  conversation_variables: []
  environment_variables:
    - name: MY_VAR
      value_type: string
      value: 'hello'
      description: ''
  features:
    file_upload: { enabled: false }
    opening_statement: ''
    retriever_resource: { enabled: false }
    sensitive_word_avoidance: { enabled: false }
    speech_to_text: { enabled: false }
    suggested_questions: []
    suggested_questions_after_answer: { enabled: false }
    text_to_speech: { enabled: false, language: '', voice: '' }
  graph:
    edges:
      - data: { isInIteration: false, isInLoop: false, sourceType: custom, targetType: custom }
        id: '1749000000001-source-1749000000002-target'
        source: '1749000000001'
        sourceHandle: source
        target: '1749000000002'
        targetHandle: target
        type: custom
        zIndex: 0
    nodes:
      - data:
          title: Schedule Trigger
          type: trigger-schedule
          cron_expression: '0 5 * * *'   # 8:00 МСК в UTC
          frequency: daily
          mode: cron                     # cron | visual
          timezone: UTC
          visual_config:
            monthly_days: [1]
            on_minute: 0
            time: '8:00 AM'
            weekdays: [sun]
        height: 129
        id: '1749000000001'
        position: { x: 80, y: 282 }
        positionAbsolute: { x: 80, y: 282 }
        sourcePosition: right
        targetPosition: left
        type: custom
        width: 242
      - data:
          title: End
          type: end
          outputs: []                   # массив {variable, value_selector}
        height: 89
        id: '1749000000002'
        position: { x: 400, y: 282 }
        positionAbsolute: { x: 400, y: 282 }
        sourcePosition: right
        targetPosition: left
        type: custom
        width: 242
    viewport: { x: 0, y: 0, zoom: 1 }
  rag_pipeline_variables: []
```

## Импорт через Console API

```bash
# YAML в JSON как string
python3 -c "
import json
yaml_content = open('workflow.yml').read()
print(json.dumps({
    'mode': 'yaml-content',
    'yaml_content': yaml_content,
    'name': 'My Workflow',
    'description': 'Test',
    'icon_type': 'emoji',
    'icon': '🚀',
    'icon_background': '#000000'
}))
" > /tmp/payload.json

curl -X POST "$DIFY_BASE_URL/console/api/apps/imports" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d @/tmp/payload.json
# → {id, status: completed, app_id, app_mode: workflow, ...}
```

## Версии DSL

| Version | Что нового |
|---|---|
| 0.6.0 | Текущая (Dify 1.14.2). Поддерживает MCP, structured output, iterations, triggers |

Dify сам проставляет версию при экспорте. При импорте если версия старше — может потребоваться миграция.

## Когда использовать DSL vs sync draft

| Сценарий | Что использовать |
|---|---|
| Создать новый workflow с нуля | DSL импорт (одним POST) |
| Изменить существующий graph | POST /workflows/draft (sync) |
| Сериализация/backup | GET /apps/{id}/export |
| Миграция между инстансами | Экспорт + импорт YAML |
