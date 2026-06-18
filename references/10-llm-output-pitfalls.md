# LLM Output Pitfalls — что идёт не так с output

Собрано из реальной практики разработки jobs-digest. Каждая проблема → симптом → причина → решение.

## 1. LLM галлюцинирует — генерит больше данных чем просили

**Симптом:** `total_classified: 709` при 137 входных сообщений. LLM возвращает 5x больше классификаций чем получил входных.

**Причина:** Маленькие модели (glm-4.7-flash, аналоги) на больших outputs (8K+ tokens) склонны к **generative loops** — начинают повторять один и тот же паттерн (например `{"type": "request", "relevance": 1}` для несуществующих uid). Достигают max_tokens с мусором.

**Решение (по убыванию сложности):**

A. **Strict count instruction в промпте:**
```
⚠️ Верни РОВНО столько классификаций, сколько сообщений получил ({{count}} шт).
НЕ БОЛЬШЕ. Если получил 50 сообщений — верни 50 классификаций.
```

B. **Перейти на более мощную модель** для classifier (glm-4.7 вместо glm-4.7-flash, или glm-5.2).

C. **Уменьшить объём входных данных** (per_chat_limit в MCP, limit в queries).

D. **Iteration с chunking** — разбить на chunks по 25-30, каждый отдельный LLM call.

## 2. JSON output обрезан по max_tokens

**Симптом:** LLM отработал 200+ секунд, `finish_reason=None` (не end_turn), text заканчивается на `...{"uid": "xxxx:14` (без закрытия).

**Причина:** `max_tokens` в completion_params достигнут раньше чем LLM завершил JSON.

**Решение:**

A. **Поднять max_tokens** (проверить что модель поддерживает — glm-4.7 = 200K context, но output обычно до 32K).

B. **Robust JSON parser с salvage regex:**
```python
import json, re

def parse_with_salvage(text: str) -> list:
    # 1. Прямой parse
    try:
        data = json.loads(text)
        return data.get('results', []) if isinstance(data, dict) else data
    except: pass
    
    # 2. Извлечь валидные объекты по pattern
    pattern = r'\{"uid":\s*"[^"]+",\s*"type":\s*"[^"]+",\s*"relevance":\s*\d+,\s*"reason":\s*"[^"]*"\}'
    matches = re.findall(pattern, text)
    return [json.loads(m) for m in matches]
```

C. **Уменьшить объём** через truncate в Format Code node:
```python
text=m.get('text', '')[:600]  # было 1500
```

## 3. Anthropic SDK не понимает response_format

**Первоначальное утверждение:**
* **Симптом**: `Messages.create() got an unexpected keyword argument 'response_format'`
* **Причина**: Dify при `structured_output_enabled=true` + наличии parameter_rule `response_format` в YAML модели автоматически добавляет `response_format: json_object` в completion_params. Anthropic SDK это не понимает.
* **Решение**: `structured_output_enabled=false` + явная инструкция в system prompt вернуть JSON. См. [06-llm-node-gotchas.md](06-llm-node-gotchas.md).

**Результат верификации (2026-06-18) ❌ ОПРОВЕРГНУТО:**
На Dify 1.14.2 с провайдером `proxyapi-openrouter` и моделью `deepseek/deepseek-v4-flash` структурированный вывод через `"structured_output_enabled": true` работает **корректно**. Dify сам запрашивает и парсит схему. См. подробнее в [llm.md](nodes/llm.md).

## 4. LLM возвращает markdown вместо JSON

**Симптом:** `json.loads(text)` падает. Текст начинается с ` ```json ` или содержит `**bold**`.

**Решение:** Добавить в system prompt:
```
Без markdown, без ```json```, чистый JSON объект.
Не добавляй текст до или после JSON.
```

Или robust parser:
```python
import re
m = re.search(r'```(?:json)?\s*(.+?)\s*```', text, re.DOTALL)
if m:
    text = m.group(1)
```

## 5. Plain text для Telegram вместо HTML/Markdown

**Симптом:**
- При `parse_mode=Markdown`: literal `###`, `---`, `-` в сообщении
- При `parse_mode=HTML`: `Bad Request: can't parse entities: Unclosed start tag`
- LLM генерит незакрытые теги когда текст > 1000 char

**Решение:** **Plain text без parse_mode**. LLM инструкцию:
```
НЕ используй HTML-теги или markdown.
Используй ТОЛЬКО: emoji, ЗАГЛАВНЫЕ БУКВЫ, переводы строк, символы │ ─ ►
Ссылки — полный URL (Telegram сам кликабельные сделает).
```

HTTP body без parse_mode:
```yaml
'{"chat_id": "...", "disable_web_page_preview": true, "text": "{{...}}"}'
```

## 6. Array indexing НЕ работает в template strings

**Симптом:** literal `{{#node.arr[0]#}}` приходит в Telegram вместо значения.

**Решение:** Code node для извлечения элемента:
```python
def main(arr: list) -> dict:
    return {"first": arr[0] if arr else ""}
```

## 7. Code node array limit (30 elements)

**Первоначальное утверждение:**
* **Симптом**: `The length of output variable 'X' must be less than 30 elements.`
* **Причина**: Dify Code node имеет хардкод лимит 30 элементов на array output. `CODE_MAX_STRING_ARRAY_LENGTH` env не помогает.
* **Решение**: Передавать массив как JSON string (`json.dumps(items)`) и парсить через `json.loads` в следующей ноде.

**Результат верификации (2026-06-18) ❌ ОПРОВЕРГНУТО:**
Тесты в реальном рантайме Dify 1.14.2 подтвердили, что жесткого лимита в 30 элементов для возвращаемого массива **нет**. Код успешно вернул и обработал массив из 500 элементов без каких-либо ошибок. Использование JSON-строк для обхода ограничения больше не требуется. См. подробнее в [code.md](nodes/code.md).


## 8. MCP tool — array параметр ломается через constant

**Симптом:** MCP возвращает 0 results, хотя Python client с теми же параметрами даёт 27.

**Решение:** `type: variable` через Code node:
```yaml
tool_parameters:
  entities:
    type: variable
    value: ['<code_node_id>', 'entities']
```

Не `type: constant` с array value — Dify ломает массив при конвертации.

## 9. MCP provider_id = server_identifier, не UUID

**Симптом:** `ToolProviderNotFoundError: mcp provider <UUID> not found`

**Решение:** В tool node `provider_id` = **server_identifier** (slug типа 'telegram-mcp'), не UUID БД. См. [05-mcp-tool-node.md](05-mcp-tool-node.md).

## 10. LLM слишком строгий после добавления exclude-правил

**Симптом:** После добавления правил "исключать Senior/English-fluent" — 0 релевантных из 84 сообщений.

**Причина:** Промпт стал слишком список-ориентированным. LLM боится ставить высокие оценки, применяет правила слишком буквально.

**Решение:**
- Ослабить шкалу: "Если стек СОВПАДАЕТ и уровень НЕ Senior — ставь минимум 4"
- Поднять relevance threshold в фильтре (или наоборот опустить — `>= 3` вместо `>= 4`)
- Тестировать и калибровать итеративно

## 11. Workflow "выглядит хорошо" но всем relevance=1

**Симптом:** Все классификации relevance=1, даже очевидно подходящие.

**Причина:** LLM трактует неоднозначности в пользу "нерелевантно" когда промпт строгий.

**Решение:** В промпте добавить explicit guidance:
```
ВАЖНО:
- Если стек СОВПАДАЕТ (Python/FastAPI/AI/LLM/Telegram) и уровень НЕ Senior — ставь минимум 4
- Если уровень middle и формат не указан — relevance 4 (не 3!)
```

## 12. Iteration для большого объёма — обязательно

**Симптом:** При 100+ элементах LLM не справляется: либо галлюцинирует, либо обрезает, либо очень долго.

**Решение:** Iteration node с chunks:
```
[Code: разбить на chunks по 25] → [Iteration: LLM per chunk] → [Code: merge results]
```

## Patterns для будущих skills

### Pattern: Incremental LLM workflow development

```
1. Создать skeleton workflow (Schedule + End)
2. Добавить data source (MCP/HTTP/Code)
3. Добавить processing Code node
4. Добавить 1 LLM node (test на 5-10 элементов)
5. Расширить до реального объёма (100+)
6. Если LLM ломается → Iteration + chunks
7. Калибровать промпты (relevance threshold, exclude rules)
8. Добавить delivery (HTTP/Telegram)
9. Publish
```

### Pattern: Robust LLM output handling

```python
# Universal LLM output parser
import json, re

def parse_llm_output(text: str, expected_key: str = 'results') -> list:
    """Parse JSON from LLM output with multiple fallbacks."""
    if not text:
        return []
    
    # 1. Direct parse
    try:
        data = json.loads(text)
        return data.get(expected_key, []) if isinstance(data, dict) else data
    except: pass
    
    # 2. Strip markdown code fence
    m = re.search(r'```(?:json)?\s*(.+?)\s*```', text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            return data.get(expected_key, []) if isinstance(data, dict) else data
        except: pass
    
    # 3. Find JSON boundaries
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end > start:
            try:
                data = json.loads(text[start:end+1])
                return data.get(expected_key, []) if isinstance(data, dict) else data
            except: pass
    
    # 4. Regex salvage individual objects
    pattern = r'\{[^{}]*"uid":[^{}]*\}'  # адаптируй под свою schema
    matches = re.findall(pattern, text)
    return [json.loads(m) for m in matches if m]
```

### Pattern: Telegram bot integration

```yaml
# HTTP Request node для Telegram sendMessage
# Plain text (без parse_mode) — самый надёжный
method: post
url: 'https://api.telegram.org/bot{{#env.BOT_TOKEN#}}/sendMessage'
body:
  type: json
  data: '{"chat_id": "{{#env.USER_ID#}}", "disable_web_page_preview": true, "text": "{{#summarizer.text#}}"}'
```

Промпт Summarizer для plain text:
```
НЕ используй HTML-теги или markdown.
Используй ТОЛЬКО: emoji, ЗАГЛАВНЫЕ БУКВЫ, переводы строк, символы │ ─ ►
Ссылки — полный URL.
```

### Pattern: Variable вместо constant для MCP array

```yaml
# ❌ НЕ работает для array параметров MCP
tool_parameters:
  entities:
    type: constant
    value: ["-1001234567890", "-100987654321"]

# ✅ Работает
# 1. Code node возвращает array
def main() -> dict:
    return {"entities": ["-1001234567890", "-100987654321"]}

# 2. MCP tool node ссылается на Code
tool_parameters:
  entities:
    type: variable
    value: ['<code_node_id>', 'entities']
```
