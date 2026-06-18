# Case Study: Jobs Digest — полная история разработки

Реальный пример разработки Dify workflow через Console API. От идеи до production за одну сессию. Все ошибки и решения задокументированы — это лучший reference для будущих skills.

## Контекст

Даниил хочет каждое утро получать сводку релевантных вакансий из Telegram-папки "Фриланс" в личку. Фильтрация: фриланс, боты, AI-интеграции, backend Python/PHP, middle+ (не Senior), без требований продвинутого английского.

## Стек

- Dify 1.14.2 self-hosted
- MCP: mcp-telegram (HTTP/SSE на https://tg.keemor.su/sse)
- LLM: glm-4.7 (Anthropic-совместимый через zai-coding-plan плагин)
- Delivery: Telegram Bot @KeemorHomeBot
- 29 каналов из папки "Фриланс"

## Архитектура (final)

```
Schedule 8:00 МСК
  → Code (date calc + 29 chat_ids)
  → MCP export_messages (вчера 00:00 → сегодня 00:00)
  → Code flatten (results → messages_json string)
  → Code format (messages_json → text для LLM)
  → LLM Classifier (glm-4.7, JSON output)
  → Code filter+dedup (relevance ≥ 3)
  → LLM Normalizer (glm-5.2, structured data)
  → Code sort (by automation_potential)
  → LLM Summarizer (glm-5.2, plain text)
  → Code chunk (для Telegram limit)
  → HTTP sendMessage (Telegram bot)
  → End
```

**12 nodes, ~80 sec total, 0 RMB cost (Coding Plan).**

## Timeline разработки (с ошибками)

### v0.1 — Skeleton

Создал app через `/apps/imports` с YAML DSL: Schedule + End + env vars.

```python
POST /console/api/apps/imports
{ mode: 'yaml-content', yaml_content: <minimal DSL> }
# → app_id: 5af1637b-...
```

**Result:** ✓ Работает. Schedule Trigger + End + 2 env vars.

### v0.2 — Code (Date Calc)

Добавил Code node для расчёта дат через `POST /workflows/draft`. Hash из GET обязателен.

```python
def main() -> dict:
    return {"start_date": "...", "end_date": "...", "yesterday_date": "..."}
```

**Result:** ✓ Работает. UTC-конвертация корректная.

### v0.3 — MCP tool node

Добавил MCP node для `export_messages`. **Первая серия багов:**

1. `provider_id: <UUID>` → `ToolProviderNotFoundError`. **Fix:** `provider_id: 'telegram-mcp'` (server_identifier).
2. `entities: {type: constant, value: [...]}` → 0 results. **Fix:** `type: variable` через Code node.
3. 0 сообщений за вчера (день без постов). **Fix:** расширить окно до 7 дней для теста.

**Result:** ✓ 27 сообщений из 1 канала.

### v0.4 — Code (Flatten)

Code для flatten MCP result в flat list. Сначала через `value_selector: ['mcp_node', 'text']` — но MCP возвращает **несколько** outputs (`text`, `json`, `results`, `chats_processed`). Нужно `results` (auto-extracted top-level key из MCP response).

**Result:** ✓ 27 flat messages с uid.

### v0.5 — LLM Classifier

Добавил LLM node с structured_output_enabled=true.

**Bug:** `Messages.create() got an unexpected keyword argument 'response_format'`. Anthropic SDK не понимает response_format.

**Fix:** `structured_output_enabled=false` + JSON инструкция в system prompt + Code parse.

**Result:** ✓ 27 → 6 релевантных вакансий (relevance ≥ 4).

### v0.6 — Full pipeline v1.0

Добавил Normalizer + Summarizer + HTTP Telegram. Всё заработало, workflow succeeded.

**Bug:** В Telegram пришёл literal `{{#node.chunks[0]#}}`. Array indexing не работает в template strings.

**Fix:** Использовал `{{#summarizer.text#}}` напрямую (chunks всегда 1 для MVP).

**Result:** ✓ Workflow end-to-end succeeded, Telegram получил осмысленный текст.

### v1.0 → v1.5 — Калибровка

| Version | Что изменил | Результат |
|---|---|---|
| v1.0 | MVP работает | Telegram получает сводку |
| v1.1 | Seniority rules (middle+ only) | LLM галлюцинирует (710 вместо 137) |
| v1.2 | English rules (no fluent) | LLM слишком строгий (0 релевантных) |
| v1.3 | max_tokens 32K + salvage regex | Всё ещё 0 релевантных |
| v1.4 | glm-4.7 + per_chat_limit=5 + strict count | 84 classified, НО 0 релевантных |
| **v1.5** | **Relaxed scoring + threshold 3** | **✓ 3 релевантные вакансии в Telegram** |

## Главные уроки (для skill)

### Урок 1: Incremental development обязателен

Не делать "большой взрыв" — добавлять по 1-2 nodes за sync:
1. Schedule + End
2. + Date Calc
3. + MCP
4. + Code flatten
5. + LLM
6. + ...

После каждой — `draft run` с проверкой outputs.

### Урок 2: LLM output — это always проблема

- JSON может быть обрезан
- LLM может галлюцинировать
- Может добавлять markdown несмотря на инструкцию

**Решение:** всегда robust parser:
```python
def parse_llm_output(text, expected_key='results'):
    # 1. direct parse
    # 2. strip markdown
    # 3. find JSON boundaries
    # 4. regex salvage individual objects
```

### Урок 3: Маленькие модели галлюцинируют на длинных output

glm-4.7-flash с max_tokens=32K генерит 710 фейковых классификаций вместо 137.

**Fix:**
- Более мощная модель (glm-4.7 вместо flash)
- Strict count instruction в промпте
- per_chat_limit / limit в источнике данных
- Iteration с chunks если объём реально большой

### Урок 4: Структурированный вывод LLM

- С нативным `structured_output_enabled: true` модели вроде `deepseek/deepseek-v4-flash` через ProxyAPI OpenRouter работают отлично.
- Для провайдеров/моделей, не поддерживающих JSON Schema нативно, надежным решением остается отключение structured output, явная инструкция в промпте вернуть JSON и последующий парсинг через Code-ноду.

### Урок 5: Ограничения массивов в Code node — обход вложенных массивов через JSON string

- Тесты опровергли наличие жесткого лимита в 30 элементов для одномерных массивов (успешно возвращаются списки по 500+ элементов).
- Однако Dify по-прежнему не поддерживает вложенные структуры (массив массивов, `array[array]`). Для их передачи между нодами используется сериализация в JSON string:

```python
import json
def main(nested_items: list) -> dict:
    return {"items_json": json.dumps(nested_items)}  # type: string
```

Все последующие ноды разбирают эту строку через `json.loads`.

### Урок 6: Telegram plain text > HTML > Markdown

- Markdown legacy: не поддерживает `###`, `---`, `-`
- MarkdownV2: требует экранирования кучи символов
- HTML: Telegram строгий — любой незакрытый `<a>` → error
- **Plain text: работает всегда**, emoji + caps + spacing для визуального выделения

### Урок 7: MCP array параметры — только через variable

`type: constant` с array value ломается где-то в graphon runtime.

```yaml
# ❌
entities: { type: constant, value: [...] }

# ✅
entities: { type: variable, value: ['<code_node>', 'entities'] }
```

### Урок 8: Промпт-калибровка итеративная

После добавления exclude-правил (Senior, English) — LLM стал слишком строгий (0 релевантных). Решение:
- Ослабить шкалу ("если стек совпадает — минимум 4")
- Опустить threshold в фильтре (4 → 3)
- Тестировать и калибровать по реальным данным

### Урок 9: Schedule Trigger cron в UTC

8:00 МСК = `0 5 * * *`. Не забывать конвертировать.

### Урок 10: Workflow iterations > 5 — нормально

10-15 итераций sync+run — нормальный цикл разработки. Не пытаться сделать всё идеально с первого раза.

## Финальные метрики

| Метрика | Значение |
|---|---|
| Время разработки | ~4 часа (включая все итерации) |
| Количество sync draft | ~20 |
| Количество draft runs | ~15 |
| Workflow nodes | 12 |
| Total execution time | ~80 сек |
| Token usage | ~7000 (3 LLM calls) |
| Cost | 0 RMB (Coding Plan) |
| App versions published | 5 (v1.0 → v1.5) |

## Применимость lessons к другим workflow

Эти уроки универсальны для любых Dify workflows с:
- MCP sources
- LLM processing
- JSON output
- Telegram/HTTP delivery

Для будущего skill — `~/defyproj/dify-workflow-dev/` содержит всё необходимое:
- API reference (01-09)
- LLM pitfalls (10)
- Case study (этот файл)
- Templates (examples/)

## Файлы проекта

| Файл | Что |
|---|---|
| `~/defyproj/jobs-digest/chat_ids.json` | 33 chat_ids (29 используются, лимит 30) |
| `~/defyproj/jobs-digest/cv.md` | CV Даниила (для reference) |
| `~/defyproj/jobs-digest/competency-profile.md` | Профиль компетенций |
| `~/defyproj/jobs-digest/career-goals.md` | Карьерные цели |
| `~/defyproj/jobs-digest/workflow-design.md` | Исходный дизайн-документ |
| `~/defyproj/.env` | Секреты (MCP, bot, workspace) |
| Dify app | ID `5af1637b-c5fc-4eb7-b985-7fd2cf7f1a4d` (v1.5 published) |
