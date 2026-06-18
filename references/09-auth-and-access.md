# Auth и доступы к Dify Console API

## Self-hosted Dify 1.14.2 — специфика

В self-hosted версии **нет Personal Access Tokens** (PAT, как в Dify Cloud). Два варианта доступа:

### 1. ADMIN_API_KEY (рекомендуется для автоматизации)

Включается в `~/dify/docker/.env`:
```
ADMIN_API_KEY_ENABLE=true
ADMIN_API_KEY=dify-admin-<64 hex chars>
```

После изменения → пересоздать api контейнер (НЕ restart):
```bash
cd ~/dify/docker && docker compose up -d api
```

**Использование:**
```bash
curl -X GET "$DIFY_BASE_URL/console/api/apps" \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
```

⚠️ **Обязательно X-WORKSPACE-ID заголовок.** Без него — 401 даже с правильным ключом.

См. `~/dify/api/extensions/ext_login.py:60` — workspace_id required.

### 2. Session login через Playwright (fallback)

Если ADMIN_API_KEY выключен или не работает:
1. Открыть UI через Playwright
2. Ввести email+password
3. Достать access_token из cookie
4. Использовать как Bearer

См. `~/defyproj/scripts/login.md` (если есть) для процесса.

Не рекомендуется для автоматизации — токен протухает через часы.

## Environment variables в `~/defyproj/.env`

```bash
# Dify instance
DIFY_BASE_URL=http://localhost:3006

# Console API
DIFY_CONSOLE_TOKEN=dify-admin-xxxx       # ADMIN_API_KEY

# Workspace
DIFY_WORKSPACE_ID=<uuid>

# Service API (per-app)
DIFY_APP_CHATBOT_KEY=app-xxx
DIFY_APP_WORKFLOW_KEY=app-xxx
DIFY_APP_AGENT_KEY=app-xxx
```

Загрузка в bash:
```bash
set -a; source ~/defyproj/.env; set +a
```

## Service API vs Console API

| | Console API | Service API |
|---|---|---|
| URL | `/console/api/*` | `/v1/*` |
| Auth | `Bearer $DIFY_CONSOLE_TOKEN` + `X-WORKSPACE-ID` | `Bearer $DIFY_APP_*_KEY` |
| Что делает | Управление всем Dify (apps, MCP, models, datasets) | Вызов конкретного приложения |
| Срок жизни | Бессрочно (ADMIN_API_KEY) | Бессрочно (per-app) |
| Документация | Нет публичной — смотреть код `~/dify/api/controllers/console/` | `~/dify-docs/en/api-reference/` |

## Смена ADMIN_API_KEY

```bash
NEW_KEY="dify-admin-$(openssl rand -hex 32)"
sed -i "s|^ADMIN_API_KEY=.*|ADMIN_API_KEY=$NEW_KEY|" ~/dify/docker/.env
cd ~/dify/docker && docker compose up -d api    # НЕ restart!
sed -i "s|^DIFY_CONSOLE_TOKEN=.*|DIFY_CONSOLE_TOKEN=$NEW_KEY|" ~/defyproj/.env
```

⚠️ `docker compose restart api` **НЕ перечитывает** `.env`. Только `up -d` (с пересозданием).

## Получение workspace_id

```bash
curl -sS "$DIFY_BASE_URL/console/api/workspaces" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: any"   # для этого endpoint — любой, он вернёт список
| jq '.workspaces[] | select(.current == true) | .id'
```

## Получение app API key (для Service API)

```bash
# Создать новый ключ
curl -X POST "$DIFY_BASE_URL/console/api/apps/{app_id}/api-keys" \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID"
# → {id, type: 'app', token: 'app-xxx', ...}
```

## Кастомные заголовки (если есть прокси/auth)

Если Dify за прокси с дополнительной auth:
```bash
curl ... \
  -H "Authorization: Bearer $DIFY_CONSOLE_TOKEN" \
  -H "X-WORKSPACE-ID: $DIFY_WORKSPACE_ID" \
  -H "X-Custom-Auth: $CUSTOM_AUTH"
```

## CSRF

Через ADMIN_API_KEY — **нет CSRF** проверки (строка 187 в `~/dify/api/libs/token.py`).

Через session login — требуется CSRF токен из cookie + заголовок `X-CSRF-Token`.

## Безопасность

- `.env` в `.gitignore`
- ADMIN_API_KEY — сложный (64 hex chars)
- Не логировать ключи в production
- X-WORKSPACE-ID не секретный, но не публиковать
- App API keys — каждый для своего app, легко ротировать

## Self-hosted specific

`FORCE_VERIFYING_SIGNATURE=false` в `~/dify/docker/.env` — позволяет ставить fork'и плагинов без официальной подписи Dify. Снижает безопасность, но нужно для разработки своих плагинов.

Пересоздать plugin_daemon после изменения:
```bash
cd ~/dify/docker && docker compose up -d plugin_daemon
```
