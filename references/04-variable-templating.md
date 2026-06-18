# Variables и Templating

## Типы переменных в workflow

### Workflow Variables (execution-local)

Переменные **внутри одной execution**. Создаются через output node и используются в следующих nodes. После завершения workflow — исчезают.

Доступ через `value_selector: ['<source_node_id>', '<output_var_name>']`.

### Environment Variables (workflow-level)

Хранятся в самом workflow (персистентные между executions). Создаются через UI Settings или через `POST /workflows/draft` payload.

```yaml
environment_variables:
  - name: BOT_TOKEN
    value_type: secret            # string | number | secret
    value: 'xxxxxxxx'
    description: 'Telegram bot token'
```

- `string` — обычная строка
- `number` — число
- `secret` — **шифруется** в БД, отображается как `****` в UI

Использование в nodes: `{{#env.BOT_TOKEN#}}`

⚠️ **Secrets всегда через `secret` тип**, не string.

### Conversation Variables (только chatflow)

Переживают multiple turns внутри одной conversation. Не для workflow mode.

### System Variables (built-in)

Доступны в любом workflow:

| Variable | Описание |
|---|---|
| `sys.user_id` | ID пользователя |
| `sys.app_id` | ID приложения |
| `sys.workflow_id` | ID workflow |
| `sys.workflow_run_id` | ID текущего execution |
| `sys.files` | Массив загруженных файлов |
| `sys.timestamp` | Unix timestamp запуска |

Использование: `{{#sys.user_id#}}`

## Variable Templating

Синтаксис: `{{#<source>.<variable>#}}` в любом текстовом поле node (prompt, URL, body, и т.д.).

### Examples

```yaml
# В prompt LLM
text: 'Process this: {{#1749000000030.messages#}}'

# В URL HTTP node
url: 'https://api.telegram.org/bot{{#env.BOT_TOKEN#}}/sendMessage'

# В body HTTP node
body:
  type: json
  data: '{"chat_id": "{{#env.TG_USER_ID#}}", "text": "{{#1749000000090.text#}}"}'

# В End outputs
outputs:
  - variable: result
    value_selector: ['1749000000080', 'vacancies']
```

### value_selector vs template string

Два способа указать значение:

**value_selector** (массив):
```yaml
variables:
  - variable: messages
    value_selector: ['1749000000030', 'messages']
```
Используется в `variables` входах Code, LLM context, и т.д. **Строго типизировано**.

**Template string** (с `{{#...#}}`):
```yaml
text: 'Hello {{#1749000000030.total#}} world'
```
Используется в prompt_template, URL, body. **Свободный текст** с подстановками.

## tool_parameters — особенности

В MCP/plugin tool nodes параметры имеют свой формат:

```yaml
tool_parameters:
  param_name:
    type: variable | constant | mixed
    value: <depends on type>
```

### type: variable

```yaml
entities:
  type: variable
  value: ['<source_node_id>', 'output_var']   # value_selector array
```

### type: constant

```yaml
limit:
  type: constant
  value: 30                                    # string | number | boolean
```

⚠️ **array через constant НЕ РАБОТАЕТ корректно для MCP!** См. [05-mcp-tool-node.md](05-mcp-tool-node.md).

### type: mixed

Template string со вставками:
```yaml
prompt:
  type: mixed
  value: 'Prefix {{#some_node.var#}} suffix'
```

## Передача массивов между nodes

```python
# Code node возвращает array
def main() -> dict:
    return {
        "items": ["a", "b", "c"],          # array[string]
        "objects": [{"x": 1}, {"x": 2}],   # array[object]
    }
```

Outputs declaration:
```yaml
outputs:
  items: { type: 'array[string]', children: null }
  objects: { type: 'array[object]', children: null }
```

⚠️ **`children: null` обязателен** для всех типов outputs, даже для scalar.

Доступ в следующей node: `value_selector: ['<code_node_id>', 'items']` или `{{#<code_node_id>.items#}}`.

⚠️ **Прямое индексирование массива в template strings НЕ поддерживается**:
```yaml
text: "{{#1749000000100.chunks[0]#}}"   # ❌ НЕ РАБОТАЕТ, пришлёт literal строку
```

**Решение (через Code node)**:
Извлечь нужный элемент в Code node и использовать его:
```python
def main(chunks: list) -> dict:
    return {"first_chunk": chunks[0] if chunks else ""}
```
И использовать `{{#code_node.first_chunk#}}`.

**Решение (через Template Transform / Jinja2)**:
В ноде Template Transform можно использовать Jinja2-индексацию:
```jinja2
{{ chunks[0] }}   #  успешно извлечёт первый элемент
```

## Iteration variable

Внутри iteration node доступна переменная `iteration_item` — текущий элемент массива:

```yaml
# Inside iteration
text: 'Process {{#iteration.iteration_item#}}'
```

## Environment Variables — программное управление

```bash
# Get all env vars
GET /console/api/apps/{app_id}/workflows/draft/environment-variables

# Add/update
POST /console/api/apps/{app_id}/workflows/draft/variables
{
  "variable_id": null,           # null для создания
  "variable_type": "environment",
  "name": "NEW_VAR",
  "value_type": "secret",
  "value": "secret-value"
}

# При sync draft — env_vars передаются в payload:
POST /console/api/apps/{app_id}/workflows/draft
{
  "graph": ...,
  "features": ...,
  "hash": ...,
  "environment_variables": [
    { "name": "VAR1", "value_type": "string", "value": "...", "description": "" }
  ],
  "conversation_variables": []
}
```

⚠️ При каждом POST draft нужно передавать **полный** список env_vars, иначе они могут сброситься.

## Variable типы в outputs declaration

| Type | Использование |
|---|---|
| `string` | Текст |
| `number` | Число |
| `boolean` | true/false |
| `object` | Объект |
| `array[string]` | Массив строк |
| `array[number]` | Массив чисел |
| `array[object]` | Массив объектов |
| `array[boolean]` | Массив bool |
| `file` | Файл |
| `array[file]` | Массив файлов |

## Array of arrays НЕ поддерживается

Dify Code node outputs **не может** содержать `array[array[X]]` (массив массивов). Например, `array[array[string]]` — будет ошибка.

**Workaround — JSON strings:**

```python
import json

# Хотим вернуть chunks по 17 элементов
def main(all_items: list) -> dict:
    chunks = [all_items[i:i+17] for i in range(0, len(all_items), 17)]
    # Каждый chunk — JSON string, не array
    return {"chunks_json": [json.dumps(c) for c in chunks]}
    # тип chunks_json: array[string]
```

Внутри Iteration node — Code node парсит JSON обратно:
```python
def main(chunk_json: str) -> dict:
    items = json.loads(chunk_json)  # обратно в array
    return {"items": items}
```

Это критично для:
- Разбивки chat_ids на chunks (33 канала → 2 chunks по 17)
- Batch processing через Iteration
- Любых cases где нужно итерировать по массивам массивов

## Code node array limit 30 элементов

**Первоначальное утверждение:**
* **Симптом**: `The length of output variable 'X' must be less than 30 elements.`
* **Причина**: `Code node` outputs не может содержать array > 30 элементов. Это hardcoded в graphon runtime, `CODE_MAX_STRING_ARRAY_LENGTH` env не помогает.
* **Workaround**: Передавать массив как JSON string (`json.dumps(big_list)`) и парсить в следующей ноде.

**Результат верификации (2026-06-18) ❌ ОПРОВЕРГНУТО:**
Тесты в реальном рантайме Dify 1.14.2 подтвердили, что жесткого лимита в 30 элементов для возвращаемого массива **нет**. Код успешно вернул и обработал массив из 500 элементов без каких-либо ошибок. Использование JSON-строк в качестве обходного пути больше не требуется (если только вам не нужно обойти ограничение `array[array]`). Подробнее см. в [code.md](nodes/code.md).

