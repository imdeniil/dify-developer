# Грабли, обходы и lessons learned

Собрано из реальной практики разработки jobs-digest workflow на Dify 1.14.2.

## 🐛 Баги и обходы

### 1. Array параметры в MCP tool ломаются через type: constant

**Симптом:** MCP tool вызывается успешно (status=succeeded), но возвращает 0 results. Через Python MCP client напрямую — те же параметры дают 27 results.

**Причина:** Dify graphon runtime неправильно кодирует `value: ["..."]` при `type: constant`. MCP получает entities не как array, а в каком-то другом формате.

**Обход:** Использовать `type: variable` через Code node:

```python
# Code node
def main() -> dict:
    return {"entities": ["-1001292405242"]}  # array of strings
```

```yaml
# MCP tool node
tool_parameters:
  entities:
    type: variable
    value: ['<code_node_id>', 'entities']
```

### 2. MCP provider_id: server_identifier vs UUID

**Симптом:** `ToolProviderNotFoundError: mcp provider <UUID> not found`.

**Причина:** Tool node ожидает `provider_id` = **server_identifier** (slug типа 'telegram-mcp'), не UUID БД-записи. См. `~/dify/api/services/tools/mcp_tools_manage_service.py:103-114`.

**Решение:** Всегда использовать server_identifier в graph.

### 3. Anthropic SDK не понимает `response_format` (при `structured_output_enabled`)

**Первоначальное утверждение:**
* **Симптом**: `Messages.create() got an unexpected keyword argument 'response_format'`.
* **Причина**: Dify при `structured_output_enabled: true` автоматически добавляет `response_format: json_object` в completion_params если у модели есть такой parameter_rule. Но Anthropic-совместимый SDK (через который работает zai-coding-plan плагин) его не принимает.
* **Решение (быстрое)**: `structured_output_enabled: false` + явная инструкция в system prompt вернуть JSON.
* **Решение (правильное)**: убрать parameter_rule `response_format` из YAML моделей в плагине, либо добавить `support_structure_output: true` для native structured output через tools.

**Результат верификации (2026-06-18) ❌ ОПРОВЕРГНУТО / РЕШЕНО:**
На Dify 1.14.2 с провайдером `proxyapi-openrouter` и моделью `deepseek/deepseek-v4-flash` структурированный вывод через `"structured_output_enabled": true` работает **успешно**. Модель возвращает распарсенный JSON в ключе `structured_output` (`{"answer": 4}`). Спецификацию ноды см. в [llm.md](nodes/llm.md).

**⚠️ Новая находка (Валидация Memory в LLM/Classifier нодах):**
Если в DSL передаётся объект `"memory"`, то поле `"window"` является **обязательным** для Pydantic-валидации в Dify worker, даже если память отключена:
```json
// ❌ Вызовет ValidationError в Dify worker:
"memory": { "enabled": false }

// ✅ Правильный формат:
"memory": {
  "enabled": false,
  "window": { "enabled": false, "size": 50 }
}
```

### 4. POST /workflows/draft с неправильным hash

**Первоначальное утверждение:**
* **Симптом**: HTTP 400, `DraftWorkflowNotSync`.
* **Решение**: Всегда перед POST делать GET чтобы получить актуальный hash. Hash меняется после каждого sync.

**Результат верификации (2026-06-18) ⚠️ ЧАСТИЧНО ПОДТВЕРЖДЕНО:**
Поведение подтверждено, но возвращаемый HTTP-статус — **409 Conflict**, а не `400`. См. также [01-console-api-endpoints.md](01-console-api-endpoints.md).

```python
# 1. GET current
draft = GET /apps/{id}/workflows/draft
# 2. Modify
modify draft['graph']
# 3. POST with old hash
POST /apps/{id}/workflows/draft with payload['hash'] = draft['hash']
# 4. Get new hash from response
```

### 5. POST /apps/imports иногда возвращает 404 без причины

**Симптом:** Тот же POST через python urllib работает, через curl 404.

**Причина:** Возможно race condition или косяк nginx buffering.

**Решение:** Просто повторить запрос. Обычно 2-я попытка работает.

### 6. Environment variables сбрасываются при sync draft

**Симптом:** После POST /workflows/draft env_vars пропадают.

**Решение:** В payload `POST /workflows/draft` всегда передавать **полный** массив environment_variables (из GET draft). Не только новые.

```python
payload = {
    "graph": graph,
    "features": features,
    "hash": hash,
    "environment_variables": draft.get("environment_variables", []),  # ВСЕ
    "conversation_variables": draft.get("conversation_variables", []),
}
```

### 7. Schedule Trigger в UTC

**Симптом:** Workflow запускается на 3 часа раньше/позже.

**Причина:** cron_expression использует UTC, не локальное время.

**Решение:** Конвертировать. 8:00 МСК = `0 5 * * *`.

```python
import datetime
local = datetime.datetime(2026, 1, 1, 8, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=3)))
utc = local.astimezone(datetime.timezone.utc)
# → 5:00 → "0 5 * * *"
```

### 8. Long-running workflow timeout

`/workflows/draft/run` имеет таймаут. Для workflows с LLM > 60 сек — нужен `--max-time 300` в curl.

### 9. Position нод важен только для UI

Nodes с неправильными position работают нормально, но в UI они наслаиваются. Для красоты — раскладывать по сетке:

```python
NODE_WIDTH = 242
NODE_SPACING = 60
def position_for_index(i):
    return {"x": 80 + i * (NODE_WIDTH + NODE_SPACING), "y": 282}
```

### 10. `position` и `positionAbsolute` должны совпадать

В UI nodes могут быть внутри групп (iteration). Для standalone nodes — position == positionAbsolute.

### 11. Array indexing НЕ работает в template strings

**Симптом:** В Telegram приходит literal `{{#node.arr[0]#}}` вместо значения.

**Причина:** Template string `{{#node_id.var_name#}}` не поддерживает `[0]` indexing. Только полное имя переменной.

**НЕправильно:**
```yaml
body:
  data: '{"text": "{{#1749000000100.chunks[0]#"}}}'
```

**Правильно:**
```python
# Code node добавил для извлечения первого элемента
def main(chunks: list) -> dict:
    return {"first_chunk": chunks[0] if chunks else ""}
```

```yaml
body:
  data: '{"text": "{{#<extractor_node_id>.first_chunk#"}}}'
```

Или если chunks всегда один — использовать source напрямую:
```yaml
# Если chunks = [summary] (count всегда 1), взять source
'{"text": "{{#<summarizer_node_id>.text#"}}'
```

### 12. Telegram parse_mode=Markdown ломает форматирование

**Симптом:** Сообщение приходит с literal `###`, `---`, `**` вместо форматирования. Или `Bad Request: can't parse entities`.

**Причина:** Telegram Markdown (legacy) поддерживает только `**bold**`, `__italic__`, `[text](url)`, `` `code` ``. НЕ поддерживает `###`, `---`, `-`, `>` blockquotes. MarkdownV2 требует экранирования `-`, `.`, `!`, `(`, `)` и т.д.

`parse_mode=HTML` тоже хрупкий — Telegram строгий, любой незакрытый `<a>` → `can't parse entities`.

**Решение (best для MVP):** **plain text без parse_mode**. LLM генерит текст с emoji + caps + spacing:

```python
# Промпт LLM:
"""
НЕ используй HTML-теги или markdown.
Используй ТОЛЬКО: emoji, ЗАГЛАВНЫЕ БУКВЫ, переводы строк, символы │ ─ ►
Ссылки — как полный URL (Telegram сам кликабельные сделает).
"""
```

HTTP body без `parse_mode`:
```yaml
body:
  data: '{"chat_id": "{{#env.USER_ID#}}", "disable_web_page_preview": true, "text": "{{#summarizer.text#}}"}'
```

Telegram сам распознает URLs и сделает их кликабельными. Emoji работают как есть.

Если хочется bold — fallback с sanitize HTML (regex проверить закрытые теги) + `parse_mode=HTML`, но это сложнее и хрупче.

### 13. If-Else node даёт 500 в сложных графах

**Первоначальное утверждение:**
* **Симптом**: Workflow run сразу возвращает `{"event":"error","code":"internal_server_error","message":"Internal Server Error, please contact support.","status":500}` без деталей. Логи api пустые.
* **Причина**: If-Else node с `cases` структурой + variable_selector на boolean из Code node — где-то в graphon валидации падает. Возможно format case_id / handle naming / variable_selector к boolean.
* **Workaround**: Заменить If-Else на **Code node с встроенной условной логикой + httpx** для side-effects.

**Результат верификации (2026-06-18) ❌ ОПРОВЕРГНУТО / РЕШЕНО:**
Утверждение о нестабильности If-Else в сложных графах не подтвердилось. В Dify 1.14.2 нода работает стабильно и поддерживает сложные графы с несколькими ветками и условиями (верифицировано тестом T-09b).

**Реальная причина сбоев:** Использование недопустимых операторов сравнения в JSON DSL. Если в условиях (conditions) передать текстовый оператор сравнения вроде `"greater-than"`, `"less-than"`, `"equal"` и т.д., это ломает graphon/worker и вызывает silent crash (вечный таймаут выполнения).

**Правильное решение:** Использовать только задокументированные символы Unicode для числовых условий:
* `>` (больше)
* `<` (меньше)
* `=` (равно)
* `≠` (не равно, Unicode `\u2260`)
* `≥` (больше или равно, Unicode `\u2265`)
* `≤` (меньше или равно, Unicode `\u2264`)

Для логических (boolean) сравнений использовать оператор `"is"` и строковые значения `"true"`/`"false"`. Подробнее см. в [if-else.md](nodes/if-else.md).

Если логика ветвления слишком сложная для визуального конструктора, её по-прежнему можно заменить на **Code node с встроенной условной логикой + httpx** для side-effects:

```python
import httpx

def main(input_data, condition_var, bot_token, user_id) -> dict:
    if condition_var:  # если failed
        httpx.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": int(user_id), "text": "Alert"},
            timeout=15
        )
        alert_sent = True
    else:
        alert_sent = False
    return {"alert_sent": alert_sent}
```

Это убирает If-Else ноду из графа полностью и делает его компактнее.

### 14. HTTP Request к самому Dify из workflow — URL должен быть через контейнер

**Симптом:** HTTP Request node к `http://localhost:3006/console/api/...` из workflow → timeout или ошибка.

**Причина:** Workflow исполняется в `plugin_daemon` контейнере. `localhost` там — сам plugin_daemon, не Dify.

**Правильные URLs** (внутренние docker network):
- API: `http://api:5001/console/api/...` (рекомендуется)
- Nginx: `http://nginx:3006/...`
- Web: `http://web:3000/...`

Не `http://localhost:3006` (это сработает только если вызывать из host bash).

### 15. Authorization в HTTP Request node — через headers, не через auth config

**Симптом:** HTTP Request с `authorization: { type: "bearer", config: { token: "{{#env.TOKEN#}}" } }` → timeout или auth не работает.

**Причина:** Variable substitution внутри `authorization.config` хрупкая в Dify 1.14.2.

**Workaround:** Auth через headers string:
```yaml
headers: 'X-WORKSPACE-ID:{{#env.WS_ID#}}\nAuthorization:Bearer {{#env.TOKEN#}}'
authorization: { type: "no-auth", config: null }
```

Перенос строки `\n` разделяет несколько headers.

### 16. Telegram chunk size = 3500 char (не 4000)

**Симптом:** При chunk size 4000 иногда обрезается последняя вакансия или ломается formatting.

**Причина:** Реальный лимит Telegram 4096 char, но нужно учитывать:
- Расширение переменных `{{#...#}}` может добавить длины
- Markdown/HTML entities если включены
- Длинные URLs раздутые

**Решение:** Chunk size **3500** для safety margin:
```python
if len(current) + len(para) + 2 > 3500:
    ...
```

### 17. Array of arrays НЕ поддерживается в Dify Code node outputs

**Симптом:** Хочешь вернуть `array[array[string]]` (массив массивов строк). Dify ругается.

**Workaround — JSON strings:**
```python
import json
def main(big_list: list) -> dict:
    chunks = [big_list[i:i+17] for i in range(0, len(big_list), 17)]
    return {"chunks": [json.dumps(c) for c in chunks]}  # array[string]
```

Внутри Iteration node — Code node парсит JSON обратно в array.

### 18. Iteration output — array, доступ через `value_selector: ['<iter_node>', 'output']`

**Симптом:** После Iteration node нужен Code чтобы собрать результаты.

**Доступ:**
```python
def main(iteration_output) -> dict:
    items = iteration_output if isinstance(iteration_output, list) else [iteration_output]
    # обрабатываем каждый item
```

`value_selector: ['<iteration_node_id>', 'output']` в Code node variables.

### 19. Postgres auth из хоста не работает через Docker proxy

**Симптом:** `password authentication failed for user "postgres"` при подключении FastAPI с хоста к `localhost:5432`. Хотя `docker exec` работает без пароля.

**Причина:** `pg_hba.conf` имеет `trust` для 127.0.0.1, но Docker port forwarding меняет source IP. Соединение приходит через Docker proxy, который не входит в trust правило.

**Решение:** Backend в **docker_default** сети (external network Dify). Подключение через `db_postgres:5432` (имя контейнера):
```yaml
# docker-compose.yml для backend
networks:
  default:
    name: docker_default
    external: true

# DATABASE_URL внутри backend
postgresql://postgres:<password>@db_postgres:5432/dify_app_state
```

### 20. HTTP body data = JSON внутри JSON — не двойное экранирование

**Симптом:** API возвращает 422 (validation error) при передаче JSON body через HTTP Request node.

**Решение:** Code node возвращает JSON как string. HTTP body data подставляет string напрямую:

```yaml
# ✅ Правильно — Code возвращает ПОЛНЫЙ JSON body
body:
  data: '{{#code_node.body_json#}}'
# где body_json = '{"messages": [{"uid": "xxx", ...}]}'

# ❌ Неправильно — двойное JSON
body:
  data: '{"messages": {{#code_node.body_json#}}}'
# code_node.body_json уже содержит {messages: [...]}
```

### 21. External state pattern для cross-execution persistence

Dify workflow **stateless между запусками**. Для cross-day dedup, feedback loop, статистики — внешний state через HTTP Request nodes.

**Архитектура:**
```
Workflow → HTTP Request → FastAPI Backend (docker_default) → PostgreSQL (dify_app_state БД)
```

**Паттерн dedup:**
1. Code node: extract uids → JSON string
2. HTTP POST `/seen` → response {seen: [already_processed_uids]}
3. Filter Code: exclude seen_uids
4. ... processing ...
5. HTTP POST `/mark-processed` после отправки → insert в БД

См. [examples/external-state-pattern.md](examples/external-state-pattern.md) для полного reference.

## ⚡ Performance / Optimization

### 1. Chunking длинных данных для LLM

Если входной массив > 25-30 элементов и каждый ~500 токенов — лучше бить на chunks и через Iteration:

```
[Code: chunk by 25] → [Iteration: LLM classifier per chunk]
```

Для < 30 элементов — один LLM call работает.

### 2. Выбор модели по задаче

- Classifier / extraction массовые → **glm-4.7-flash** (дёшево)
- Normalization / summarization с качеством → **glm-5.2**
- Long context > 50K → glm-4.7 / glm-5 (200K context)

### 3. Time для LLM calls

| Operation | Среднее время |
|---|---|
| Classifier на 25-30 сообщений (glm-4.7-flash) | 20-30 сек |
| Normalizer на 5-10 вакансий (glm-5.2) | 8-15 сек |
| Summarizer на 5 вакансий (glm-5.2) | 5-10 сек |

Полный workflow jobs-digest (12 nodes): **40-60 сек**.

### 4. retry_config для нестабильных MCP/LLM

```yaml
retry_config:
  enabled: true
  max_retries: 2
  retry_interval: 2000
```

Особенно для MCP servers на удалённых машинах.

## 🎯 Best practices

### 1. ID нод — timestamp-based строки

```python
import time
base_id = str(int(time.time() * 1000))   # '1749000000010'
```

Уникально, читаемо, sort by creation time.

### 2. Naming convention для nodes

```
Schedule Trigger   → 'schedule' / 'trigger'
Code               → 'code_<purpose>' ('code_date_calc', 'code_flatten')
LLM                → 'llm_<role>' ('llm_classifier', 'llm_normalizer')
MCP                → 'mcp_<tool>' ('mcp_export_messages')
HTTP               → 'http_<service>' ('http_telegram')
End                → 'end'
```

В UI видно `title`, ID для внутренней навигации.

### 3. Environment variables для секретов

Никогда не хардкодить:
- API keys
- Bot tokens
- URLs с credentials
- Chat IDs

Только через environment variables с `value_type: secret`.

### 4. Iterative development

Не делать "большой взрыв" — добавлять nodes по 1-2 за sync:

1. Start + End
2. + Schedule Trigger
3. + First data source (MCP / HTTP)
4. + First processing (Code)
5. + LLM node
6. + etc.

После каждой итерации — draft run, проверка outputs.

### 5. Outputs declaration обязательна

Code node без `outputs` декларации не отдаст данные правильно:

```yaml
# ПРАВИЛЬНО
outputs:
  result: { type: string, children: null }
  count: { type: number, children: null }

# НЕПРАВИЛЬНО (variables не будут доступны)
# (нет outputs)
```

### 6. `children: null` обязателен для всех типов

Даже для scalar:
```yaml
outputs:
  simple_string: { type: string, children: null }   # ← children: null
```

### 7. Tests через draft run перед publish

Draft run НЕ активирует Schedule Trigger. Можно тестировать безопасно. Только после проверки → publish.

### 8. Backup через export

```bash
GET /console/api/apps/{app_id}/export > backup.yml
```

Перед большими изменениями — сохранить backup.

## 🔮 Lessons для следующего раза

### Что делал хорошо в jobs-digest

1. **Incremental sync draft** — по 1-2 nodes за итерацию
2. **Draft run после каждой** — ловил ошибки сразу
3. **Structured Output отключил** — нашёл workaround через prompt
4. **Variable для array в MCP** — обошёл баг Dify
5. **Code для date calc** — не зависит от sys.timestamp

### Что можно было лучше

1. **Дебаг через UI тоже** — иногда визуально быстрее чем SSE парсинг
2. **Сначала test на 1 канале** — быстрее iteration
3. **Перед написанием graph** — посмотреть существующие apps через export для reference

### Что добавить в v2 workflow

1. **Iteration для chunked classification** — для 100+ сообщений
2. **Iteration для multi-chunk Telegram send** — для длинных сводок
3. **Error handler** — if-else после каждой critical node
4. **Notifications** — отправлять ошибку в Telegram если workflow_failed
5. **Retry config** — для нестабильных MCP

## Versioning and updates

Dify обновляется. После апгрейда:
1. Проверить что существующие workflows не сломались
2. Запустить `GET /apps/{id}/workflows/draft` — если schema поменялась, Dify может потребовать миграцию
3. Test run всех workflows
4. Update этого reference если новые features появились
