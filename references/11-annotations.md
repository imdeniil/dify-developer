# Annotations (Annotation Reply) — Верифицировано на Dify 1.14.2

> **Статус**: верифицировано полностью. CRUD аннотаций — ✅. Включение Annotation Reply (semantic match) — ✅ через ProxyAPI OpenRouter (модели: `qwen/qwen3-embedding-8b`, `perplexity/pplx-embed-v1-4b`, `intfloat/multilingual-e5-large`).

## Что такое Annotation Reply

Annotation Reply — механизм **детерминированного Q&A** поверх LLM-ответов. Когда пользователь задаёт вопрос — система сначала ищет совпадение в базе аннотаций, и если находит — возвращает **зафиксированный ответ**, минуя LLM.

Применение:
- FAQ-боты с гарантированными точными ответами
- Исправление ошибочных ответов модели
- Ответы на частые вопросы без токен-расхода

**Работает только в Chatbot и Agent apps** (не в Workflow).

---

## Endpoint Map

| Метод | URL | Что делает |
|---|---|---|
| `GET` | `/console/api/apps/{app_id}/annotations` | Список аннотаций (пагинация + keyword search) |
| `POST` | `/console/api/apps/{app_id}/annotations` | Создать Q&A пару |
| `POST` | `/console/api/apps/{app_id}/annotations/{annotation_id}` | Обновить Q&A пару (**не** PUT!) |
| `DELETE` | `/console/api/apps/{app_id}/annotations/{annotation_id}` | Удалить аннотацию → HTTP 204 |
| `GET` | `/console/api/apps/{app_id}/annotation-setting` | Статус Annotation Reply (enabled/disabled) |
| `POST` | `/console/api/apps/{app_id}/annotation-reply/{action}` | Включить/выключить Annotation Reply (`enable`/`disable`) |
| `GET` | `/console/api/apps/{app_id}/annotation-reply/{action}/status/{job_id}` | Статус async-job включения |
| `GET` | `/console/api/apps/{app_id}/annotations/{annotation_id}/hit-histories` | История совпадений для аннотации |

> ⚠️ Обновление аннотации — через `POST /annotations/{id}`, не `PUT`. `PUT` возвращает `405 Method Not Allowed`.

---

## Примеры curl (верифицированы)

### Создание аннотации

```bash
curl -sS -X POST "$DIFY_BASE_URL/console/api/apps/$APP_ID/annotations" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Dify?", "answer": "Dify is an open-source LLM application development platform."}'
```

Ответ:
```json
{
  "id": "9d69919b-8c3d-4699-b248-729ca81aabc2",
  "question": "What is Dify?",
  "answer": "Dify is an open-source LLM application development platform.",
  "hit_count": 0,
  "created_at": 1781761509
}
```

### Обновление аннотации (POST, не PUT)

```bash
curl -sS -X POST "$DIFY_BASE_URL/console/api/apps/$APP_ID/annotations/$ANN_ID" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Dify?", "answer": "Updated answer."}'
```

### Список аннотаций

```bash
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID/annotations?page=1&limit=20&keyword=dify" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

### Удаление (HTTP 204)

```bash
curl -sS -X DELETE "$DIFY_BASE_URL/console/api/apps/$APP_ID/annotations/$ANN_ID" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

---

## Включение Annotation Reply (async job)

Annotation Reply включается асинхронно через Celery worker. Нужно поллить статус:

```bash
# 1. Запустить включение
RESP=$(curl -sS -X POST "$DIFY_BASE_URL/console/api/apps/$APP_ID/annotation-reply/enable" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "score_threshold": 0.85,
    "embedding_provider_name": "langgenius/zhipuai/zhipuai",
    "embedding_model_name": "embedding-2"
  }')
JOB_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

# 2. Поллить статус (каждые 2 сек)
curl -sS "$DIFY_BASE_URL/console/api/apps/$APP_ID/annotation-reply/enable/status/$JOB_ID" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
# → {"job_id": "...", "job_status": "succeeded"} или "error"
```

Поля для `POST annotation-reply/enable`:

| Поле | Тип | Обязательно | Описание |
|---|---|---|---|
| `score_threshold` | float | ✅ | Порог схожести (0.0–1.0). Рекомендуется 0.85–0.9 |
| `embedding_provider_name` | string | ✅ | Провайдер embedding-модели (полный путь: `langgenius/zhipuai/zhipuai`) |
| `embedding_model_name` | string | ✅ | Имя embedding-модели |

> ⚠️ Поля называются `embedding_provider_name` и `embedding_model_name` (не `embedding_provider` + `embedding_model`). Неправильные имена → `400 invalid_param`.

Узнать default embedding provider:
```bash
curl -sS "$DIFY_BASE_URL/console/api/workspaces/current/default-model?model_type=text-embedding" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
# → {"data": {"model": "embedding-2", "provider": {"provider": "langgenius/zhipuai/zhipuai", ...}}}
```

---

## Ограничения и gotchas

### Embedding model должна реально работать

Annotation Reply требует рабочую text-embedding модель. В нашем окружении:
- `langgenius/zhipuai/zhipuai` + `embedding-2` — настроен как **default embedding**, НО Z.AI API key не даёт доступа к embedding-моделям (ошибка 1211).
- `imdeniil/zai-coding-plan/zai_coding_plan` — **не поддерживает** text-embedding (только LLM).
- **Решение**: Мы разработали и установили кастомный плагин `imdeniil/proxyapi-openrouter` (v1.0.6), настроив его с API-ключом ProxyAPI (`sk-awarMbODA...`).
  - Из плагина были исключены неработающие модели: `nvidia/llama-nemotron-embed-vl-1b-v2:free` (возвращает 404 guardrail restrictions на OpenRouter) и `google/gemini-embedding-2` (отклоняется ProxyAPI с требованием использовать выделенный эндпоинт Gemini).
  - Были добавлены и протестированы новые модели: `perplexity/pplx-embed-v1-4b` (размер контекста 32768) и `intfloat/multilingual-e5-large` (размер контекста 512).
  - Все три модели (`qwen/qwen3-embedding-8b`, `perplexity/pplx-embed-v1-4b`, `intfloat/multilingual-e5-large`) **успешно работают** и возвращают вектора при прямых запросах и через Dify RAG.
  - Асинхронная задача включения Annotation Reply (`enable`) успешно завершается со статусом `completed` при использовании этих моделей.
  - При запросе к chatbot с точным или семантическим совпадением возвращается сохранённый ответ из метаданных `annotation_reply` с нулевым токен-расходом и латенси ~0.02 сек.

### Только для chat-режимов

Annotations доступны только для `mode: chat` и `mode: agent` apps. Для `mode: workflow` — нет.

### hit_count — read-only

Dify автоматически инкрементирует `hit_count` при каждом semantic match. Нельзя задать вручную.

---

## Batch Import из CSV

```bash
curl -sS -X POST "$DIFY_BASE_URL/console/api/apps/$APP_ID/annotations/batch-import" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -F "file=@annotations.csv"
# CSV формат: question,answer (заголовок обязателен)
```

Статус: `GET /console/api/apps/{app_id}/annotations/batch-import-status/{job_id}`

Ограничения (из кода): rate limit + concurrency limit (один импорт за раз).

---

## Паттерн: создание FAQ-базы программно

```python
import requests

headers = {
    "Authorization": f"Bearer {CONSOLE_TOKEN}",
    "X-WORKSPACE-ID": WORKSPACE_ID,
}

faq_pairs = [
    {"question": "How do I reset my password?", "answer": "Settings > Security > Reset Password."},
    {"question": "What payment methods?", "answer": "Visa, Mastercard, PayPal."},
]

for pair in faq_pairs:
    resp = requests.post(f"{BASE_URL}/console/api/apps/{APP_ID}/annotations", headers=headers, json=pair)
    ann = resp.json()
    print(f"Created: {ann['id']} -> {ann['question'][:50]}")
```
