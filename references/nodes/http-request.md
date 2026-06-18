# HTTP Request Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.

## Что это

Нода для выполнения HTTP запросов к внешним или внутренним API.

## Базовая структура (DSL)

```json
{
  "id": "http_node_id",
  "type": "custom",
  "data": {
    "title": "Call API",
    "type": "http-request",
    "method": "post",
    "url": "https://api.example.com/endpoint",
    "authorization": { "type": "no-auth", "config": null },
    "headers": "Content-Type:application/json\nX-Custom-Header:value",
    "params": "key=value&other=123",
    "body": {
      "type": "json",
      "data": "{\"field\": \"{{#prev_node.output#}}\"}"
    },
    "variables": [],
    "timeout": {
      "connect": 10, "read": 60, "write": 60,
      "max_connect_timeout": 10, "max_read_timeout": 60, "max_write_timeout": 60
    },
    "ssl_verify": true
  },
  "position": { "x": 400, "y": 282 },
  "positionAbsolute": { "x": 400, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89
}
```

## Outputs

| Переменная | Тип | Описание |
|-----------|-----|---------|
| `status_code` | number | HTTP статус (200, 404, 500...) |
| `body` | string | Тело ответа |
| `headers` | object | Заголовки ответа |
| `files` | array | Файлы (если есть) |

Доступ: `value_selector: ["http_node_id", "status_code"]`

## Методы

```
get | post | put | delete | patch | head
```

## Body types

```json
{ "type": "none",                 "data": "" }
{ "type": "json",                 "data": "{\"key\": \"value\"}" }
{ "type": "raw",                  "data": "plain text" }
{ "type": "form-data",            "data": "..." }
{ "type": "x-www-form-urlencoded","data": "key=value" }
```

## Variable substitution в URL и body

```
URL:     https://api.example.com/{{#start.user_id#}}/data
Headers: Authorization:Bearer {{#env.API_KEY#}}
Body:    {"text": "{{#llm_node.text#}}", "count": {{#code.count#}}}
```

⚠️ **НЕ работает**: `{{#node.array[0]#}}` — индексация в Dify-синтаксисе не поддерживается.
Обходной путь: Code нода извлекает нужный элемент.

## Authorization — верифицированные результаты

**T-07 тест: httpbin.org/bearer с токеном "my-secret-token"**

### ✅ Через headers string — РАБОТАЕТ

```json
{
  "authorization": { "type": "no-auth", "config": null },
  "headers": "Authorization:Bearer my-secret-token"
}
```
Результат: HTTP 200, `{"authenticated": true, "token": "my-secret-token"}`

### ⚠️ Через auth config — ЗАВИСАЕТ (timeout)

```json
{
  "authorization": {
    "type": "bearer",
    "config": { "token": "my-secret-token" }
  },
  "headers": ""
}
```
Результат: workflow не завершается в течение 30-60 секунд.

> **Вывод**: Всегда используй `headers` string для Authorization, не `authorization.config`.

### Authorization через env variable

```json
{
  "authorization": { "type": "no-auth", "config": null },
  "headers": "Authorization:Bearer {{#env.API_KEY#}}\nContent-Type:application/json"
}
```

Несколько заголовков — через `\n` разделитель.

## Внутренние URL (из workflow в Dify)

Workflow выполняется в sandbox/plugin_daemon контейнере. `localhost` — это не хост машина!

```
✅  http://api:5001/console/api/...      — Dify backend API
✅  http://nginx:3006/...                — через nginx
❌  http://localhost:3006/...            — не работает из контейнера
```

## Body — передача JSON переменных

### Простая переменная в JSON body

```json
{
  "type": "json",
  "data": "{\"text\": \"{{#llm.text#}}\", \"chat_id\": \"{{#env.CHAT_ID#}}\"}"
}
```

### Целый JSON из Code ноды (без двойного вложения)

```python
# Code node возвращает готовый JSON string:
def main(items: list) -> dict:
    import json
    body = {"messages": items, "count": len(items)}
    return {"body_json": json.dumps(body)}
```

```json
{
  "type": "json",
  "data": "{{#code_node.body_json#}}"
}
```

❌ НЕ делай двойное вложение:
```json
"data": "{\"messages\": {{#code.body_json#}}}"
```

## Обработка ответа

`body` — всегда **string**. Если нужно парсить JSON:

```python
# Code нода после HTTP Request:
def main(response_body: str) -> dict:
    import json
    data = json.loads(response_body)
    return {"result": data.get("result", ""), "count": data.get("count", 0)}
```

## Когда использовать HTTP node vs Code node с httpx

| Сценарий | HTTP node | Code + httpx |
|----------|-----------|-------------|
| Простой GET/POST | ✅ | можно |
| Условный запрос (if X: send) | ❌ нужен If-Else | ✅ проще |
| Параллельные запросы | ✅ (parallel nodes) | сложнее |
| Нужен auth через config | ⚠️ зависает | N/A |
| Нужен auth через headers | ✅ | ✅ |
| Retry логика | через retry_config | через try/except |

## Retry config

```json
"retry_config": {
  "enabled": true,
  "max_retries": 3,
  "retry_interval": 2000,
  "exponential_backoff": { "enabled": false, "multiplier": 2, "max_interval": 10000 }
}
```
