# External State Pattern — PostgreSQL + FastAPI для cross-execution state

Dify workflow **stateless между запусками**. Для cross-day dedup, feedback loop, статистики — нужен внешний state. Этот pattern описывает как подключить.

## Архитектура

```
Dify Workflow (plugin_daemon)
  → HTTP Request → FastAPI Backend (docker_default network)
                      → PostgreSQL (docker-db_postgres-1, БД dify_app_state)
```

⚠️ Backend должен быть в **docker_default** сети (той же что и Dify containers). Иначе Dify не достучится.

## Компоненты

### 1. PostgreSQL — отдельная БД в существующем контейнере

```sql
-- Создать БД (не использовать основную dify!)
CREATE DATABASE dify_app_state;

-- Таблица processed_messages
CREATE TABLE processed_messages (
    uid VARCHAR(255) PRIMARY KEY,
    chat_id VARCHAR(64),
    chat_title VARCHAR(255),
    title VARCHAR(500),
    relevance INT,
    first_seen DATE NOT NULL,
    last_seen DATE NOT NULL,
    sent_to_telegram BOOLEAN DEFAULT TRUE,
    feedback VARCHAR(32),  -- 'good' | 'skip' | null
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_processed_last_seen ON processed_messages(last_seen);
CREATE INDEX idx_processed_feedback ON processed_messages(feedback);
```

### 2. FastAPI Backend — Docker container

```
state-api/
├── main.py           — FastAPI app с endpoints
├── Dockerfile         — python:3.12-slim + pip install
├── docker-compose.yml — service в docker_default сети
└── requirements.txt   — fastapi, uvicorn, asyncpg
```

**docker-compose.yml (ключевое):**
```yaml
services:
  state-api:
    build: .
    container_name: jobs-digest-state-api
    ports:
      - "8766:8766"
    environment:
      DATABASE_URL: postgresql://postgres:<DB_PASSWORD>@db_postgres:5432/dify_app_state
    networks:
      - default
    restart: unless-stopped

networks:
  default:
    name: docker_default      # ← КРИТИЧНО: external Dify network
    external: true
```

⚠️ `db_postgres` — имя postgres контейнера в docker network (не localhost!).

### 3. Endpoints

| Method | Path | Назначение |
|---|---|---|
| GET | `/health` | Healthcheck |
| POST | `/seen` | Bulk check uids: `{uids: [...]}` → `{seen: [...]}` |
| POST | `/mark-processed` | Bulk insert: `{messages: [{uid, title, ...}]}` → `{inserted: N}` |
| GET | `/feedback/{uid}` | Get feedback |
| POST | `/feedback/{uid}` | Set feedback: `{feedback: "good"\|"skip"}` |
| GET | `/stats` | Статистика |

## Интеграция в Dify Workflow

### Environment Variable

```yaml
environment_variables:
  - name: STATE_API_URL
    value_type: string
    value: 'http://jobs-digest-state-api:8766'   # ← container name:port
```

### Node 1: Check Seen (ПЕРЕД обработкой)

```yaml
- data:
    title: Check Seen
    type: http-request
    method: post
    url: '{{#env.STATE_API_URL#}}/seen'
    headers: 'Content-Type:application/json'
    body:
      type: json
      data: '{"uids": {{#extract_uids_node.uids_json#}}}'
```

⚠️ Body data — **JSON внутри JSON**. Code node должен вернуть `uids_json` как string `"uid1","uid2","uid3"` (без скобок, с запятыми). Полный body: `{"uids": ["uid1","uid2"]}`.

### Node 2: Filter (exclude seen uids)

```python
def main(classification: str, originals_json: str, seen_response: str) -> dict:
    """Filter: vacancy + relevance>=3 + NOT in seen_uids."""
    # Parse seen uids
    seen_uids = set()
    try:
        seen_data = json.loads(seen_response)
        seen_uids = set(seen_data.get("seen", []))
    except: pass
    
    # ... filter logic ...
    for c in results:
        if c.get("type") == "vacancy" and c.get("relevance", 0) >= 3:
            uid = c.get("uid", "")
            if uid in seen_uids:
                dedup_skipped += 1
                continue  # SKIP already seen
            # ... add to relevant ...
    
    return {"vacancies_json": ..., "kept": ..., "dedup_skipped": dedup_skipped}
```

### Node 3: Mark Processed (ПОСЛЕ отправки)

```yaml
- data:
    title: Mark Processed
    type: http-request
    method: post
    url: '{{#env.STATE_API_URL#}}/mark-processed'
    headers: 'Content-Type:application/json'
    body:
      type: json
      data: '{{#format_mark_node.body_json#}}'   # полный JSON body из Code
```

Code node форматирует vacancies → JSON body для API:
```python
def main(vacancies_json: str) -> dict:
    vacancies = json.loads(vacancies_json)
    messages = [{"uid": v["uid"], "title": v.get("title"), ...} for v in vacancies]
    return {"body_json": json.dumps({"messages": messages})}
```

## ⚠️ Грабли

### Postgres auth из хоста не работает

**Симптом:** `password authentication failed for user "postgres"` при подключении с хоста.

**Причина:** `pg_hba.conf` имеет `trust` для 127.0.0.1, но Docker port forwarding меняет source IP. Соединение приходит через Docker proxy IP, который не входит в trust правило.

**Решение:** Backend в **docker_default** сети. Подключение через `db_postgres:5432` (имя контейнера), не `localhost:5432`.

### HTTP body data = JSON внутри JSON

**Симптом:** API возвращает 422 (validation error) — body приходит некорректно.

**Решение:** Code node возвращает JSON как string. HTTP body data использует `{{#code.body_json#}}` — Dify подставляет **значение** string напрямую, без дополнительного экранирования.

```yaml
# ✅ Правильно
body:
  data: '{{#code_node.body_json#}}'   # body_json = '{"messages": [...]}'

# ❌ Неправильно (двойное JSON)
body:
  data: '{"messages": {{#code_node.body_json#}}}'   # body_json уже содержит {messages: ...}
```

### Variable substitution в URL

```yaml
url: '{{#env.STATE_API_URL#}}/seen'
# ✅ Подставится: http://jobs-digest-state-api:8766/seen
```

## Файлы проекта

```
~/defyproj/jobs-digest/state-api/
├── main.py              (FastAPI app, ~230 строк)
├── Dockerfile           (python:3.12-slim)
├── docker-compose.yml   (docker_default network)
└── requirements.txt     (fastapi, uvicorn, asyncpg)
```

## Запуск

```bash
cd ~/defyproj/jobs-digest/state-api
docker compose up -d --build

# Healthcheck
curl http://localhost:8766/health
# → {"status":"ok","messages":N}

# Logs
docker logs jobs-digest-state-api -f
```

## Расширения

### Phase 4: Telegram bot feedback commands

Backend webhook для Telegram bot commands:
- `/skip <uid>` → POST /feedback/{uid} {"feedback": "skip"}
- `/good <uid>` → POST /feedback/{uid} {"feedback": "good"}
- `/stats` → GET /stats → format → send to user

### Phase 5: Langfuse integration

Добавить Langfuse tracing в FastAPI middleware:
```python
from langfuse import Langfuse
langfuse = Langfuse()

@app.middleware("http")
async def trace(request, call_next):
    with langfuse.start_as_current_span("state-api"):
        return await call_next(request)
```
