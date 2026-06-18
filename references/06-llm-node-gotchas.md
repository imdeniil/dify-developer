# LLM Node — грабли и нюансы

## Общая структура

См. [03-node-types.md](03-node-types.md) → `llm` section.

## Грабли

### 1. Anthropic-совместимые модели НЕ понимают `response_format`

**Первоначальное утверждение:**
* **Проблема**: `Messages.create() got an unexpected keyword argument 'response_format'`. Это происходит, когда Dify передаёт OpenAI-совместимый параметр `response_format: 'json_object'` напрямую в Anthropic SDK.
* **Решение**: Убрать `response_format` и использовать prompt-инжиниринг с последующим парсингом в Code node.

**Результат верификации (2026-06-18) ❌ ОПРОВЕРГНУТО:**
На Dify 1.14.2 с провайдером `proxyapi-openrouter` и моделью `deepseek/deepseek-v4-flash` структурированный вывод через `"structured_output_enabled": true` работает **корректно**. Dify сам запрашивает и парсит схему. См. подробнее в [llm.md](nodes/llm.md).

### 2. structured_output_enabled + parameter_rule `response_format` = конфликт

**Первоначальное утверждение:**
* **Симптом**: Если в YAML модели провайдера в плагине есть `parameter_rule` `response_format`, и включено `structured_output_enabled: true` → Dify автоматически добавит `response_format: json_object` в completion_params, что ломает вызов в Anthropic SDK.
* **Решение**: Отключить `structured_output_enabled`, либо убрать `response_format` из YAML модели.

**Результат верификации (2026-06-18) ⚠️ РЕШЕНО/ЧАСТИЧНО ОПРОВЕРГНУТО:**
На современных версиях и моделях конфликты с SDK решены, структурированный вывод работает без ошибок. Единственным критичным ограничением является **обязательность** правильного задания объекта `window` при передаче объекта `memory` (даже если `enabled: false`), иначе Dify worker упадет с Pydantic `ValidationError`. Подробнее см. в [llm.md](nodes/llm.md).

### 3. reasoning_content в output

Для reasoning моделей (например `glm-4.5-flash`) Dify отдаёт output:

```python
outputs = {
    'text': 'основной ответ',
    'reasoning_content': '<think>...</think>',  # для reasoning моделей
    'usage': { ... }
}
```

Всегда использовать `text`, не `reasoning_content`.

### 4. Variable templating в prompt

Синтаксис: `{{#<node_id>.<var>#}}` (не Jinja2 в основном prompt_template).

**НЕ работает:**
- `{variable}` (без `#`)
- `${variable}`
- `%variable%`

**Работает:**
- `{{#1749000000030.total#}}`
- `{{#sys.user_id#}}`
- `{{#env.BOT_TOKEN#}}`

### 5. Multi-line strings в prompt

YAML поддерживает `|` для multi-line:
```yaml
prompt_template:
  - role: system
    text: |
      Line 1
      Line 2
      
      Line 4
    edition_type: basic
```

### 6. edition_type

```yaml
edition_type: basic      # статичный текст
edition_type: jitter     # chat history jitter (для multi-turn)
```

Для большинства случаев `basic`.

### 7. Memory и context

```yaml
memory:
  enabled: false         # для workflow обычно false
  window: { enabled: false, size: 50 }

context:
  enabled: false         # для RAG
  variable_selector: []  # если enabled — указать source
```

Для workflow обычно все disabled.

### 8. retry_config

```yaml
retry_config:
  enabled: false
  max_retries: 1
  retry_interval: 1000   # ms
  exponential_backoff:
    enabled: false
    multiplier: 2
    max_interval: 10000
```

Если LLM нестабилен (429/500) — включить с retry.

**Production config (recommended):**
```yaml
retry_config:
  enabled: true
  max_retries: 3
  retry_interval: 5000
  exponential_backoff:
    enabled: true
    multiplier: 2
    max_interval: 30000
```

Подходит для:
- Z.ai периодически `overloaded_error` (code 1305)
- Anthropic 429 rate limits
- Временные сетевые сбои

Backoff: 5s → 10s → 20s (capped at 30s). 3 retries = до ~65s worst case перед fail.

⚠️ **Retry добавляет latency** — если LLM критичен по времени, установить max_retries=2.

### 9. Vision

```yaml
vision:
  enabled: false
  configs: { variable_selector: [] }
```

Для моделей с поддержкой vision — указать variable_selector на file(s).

### 10. Multiple messages в prompt_template

Поддерживается:
```yaml
prompt_template:
  - role: system
    text: 'You are X.'
  - role: user
    text: 'Process this: {{#x.y#}}'
  - role: assistant
    text: 'Got it.'
  - role: user
    text: 'Now do Y.'
```

Для chat models — это история сообщений.

## Model selection cheatsheet

| Задача | Модель | Почему |
|---|---|---|
| Классификация (много вызовов, простой output) | glm-4.7-flash | Быстро, дёшево |
| Extraction / structured data | glm-5.2 | Качественнее, точнее |
| Summarization | glm-5.2 | Качественный markdown |
| Long context (>50K tokens input) | glm-4.7 / glm-5 | Context 200K |
| Cheap chat | glm-4.7-flash | Бесплатно в Coding Plan |

⚠️ glm-4.7-flash и glm-4.7 — разные модели. **flash** быстрее и дешевле.

## JSON parsing с fallback

LLM может возвращать JSON с префиксом/суффиксом или markdown обёрткой. Robust parser:

```python
import json
import re

def parse_llm_json(text: str) -> dict | list | None:
    """Parse JSON из LLM output с fallback для распространённых проблем."""
    if not text:
        return None
    
    # 1. Прямой parse
    try:
        return json.loads(text)
    except: pass
    
    # 2. Извлечь из ```json ... ``` блоков
    m = re.search(r'```(?:json)?\s*(.+?)\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except: pass
    
    # 3. Найти первый { или [ и последнее } или ]
    start = -1
    for i, c in enumerate(text):
        if c in '[{':
            start = i
            break
    if start == -1:
        return None
    
    end = -1
    for i in range(len(text) - 1, start, -1):
        if text[i] in ']}':
            end = i + 1
            break
    
    if end == -1:
        return None
    
    try:
        return json.loads(text[start:end])
    except:
        return None
```

Использовать в Code node после LLM.

## Testing LLM nodes в изоляции

Через `draft/run` можно тестировать весь workflow, но не отдельные nodes.

**Workaround**: создать mini-workflow с одной LLM node и входным Code node для тестов:

```
[Start] → [Code: hardcoded input] → [LLM target] → [End: llm output]
```

Запускать через `POST /apps/{id}/workflows/draft/run` и смотреть outputs LLM node.

Альтернатива — `POST /console/api/apps/{id}/workflows/draft/nodes/{node_id}/run` (если поддерживается для LLM).
