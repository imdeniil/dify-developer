> ⚠️ ИСТОЧНИК ИСТИНЫ: Pydantic-схема в бэкенде Dify (в пакете graphon.nodes (в entities.py для trigger)).
> Если референс расходится с кодом — код прав. Перед генерацией DSL сверяй поля.

# Trigger Nodes — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.

## Что это

Триггерные ноды (`trigger`) используются в качестве стартовых узлов для автоматического запуска **Workflow** (но не Chatflow) без участия пользователя. Они заменяют или дополняют стандартную ноду `start`.

В Dify v1.14.2 поддерживаются три типа триггеров:
1. **Trigger Schedule** (`trigger-schedule`) — запуск по расписанию (cron).
2. **Trigger Webhook** (`trigger-webhook`) — запуск по внешнему HTTP-вызову.
3. **Trigger Plugin** (`trigger-plugin`) — запуск при возникновении события в установленном плагине.

---

## 1. Schedule Trigger (`trigger-schedule`)

Запускает workflow по расписанию с использованием cron-выражений или визуального конфигуратора.

### Структура в DSL (Режим cron)

```json
{
  "id": "schedule_trigger_id",
  "type": "custom",
  "data": {
    "title": "Cron Schedule",
    "type": "trigger-schedule",
    "mode": "cron",
    "cron_expression": "0 5 * * *",
    "timezone": "UTC"
  },
  "position": { "x": 80, "y": 282 },
  "positionAbsolute": { "x": 80, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89
}
```

### Структура в DSL (Режим visual)

```json
{
  "id": "schedule_trigger_id",
  "type": "custom",
  "data": {
    "title": "Visual Schedule",
    "type": "trigger-schedule",
    "mode": "visual",
    "frequency": "daily",
    "timezone": "UTC",
    "visual_config": {
      "on_minute": 0,
      "time": "8:00 AM",
      "weekdays": ["mon", "wed", "fri"]
    }
  },
  "position": { "x": 80, "y": 282 },
  "positionAbsolute": { "x": 80, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89
}
```

### ⚠️ Критические особенности расписания:
- **Часовой пояс UTC**: Бэкенд Dify (Celery Beat) обрабатывает расписание строго в часовом поясе **UTC**.
  Пример: Для запуска в 8:00 по Московскому времени (UTC+3) cron-выражение должно быть настроено на 5:00 UTC: `0 5 * * *`.

---

## 2. Webhook Trigger (`trigger-webhook`)

Позволяет запускать workflow внешними HTTP POST запросами. При создании триггера Dify генерирует уникальный URL вебхука.

### Структура в DSL

```json
{
  "id": "webhook_trigger_id",
  "type": "custom",
  "data": {
    "title": "HTTP Webhook",
    "type": "trigger-webhook",
    "method": "post",
    "content_type": "application/json",
    "headers": [],
    "params": [],
    "body": [
      {
        "name": "payload_text",
        "type": "string",
        "required": true
      },
      {
        "name": "event_id",
        "type": "number",
        "required": false
      }
    ],
    "status_code": 200,
    "response_body": ""
  },
  "position": { "x": 80, "y": 282 },
  "positionAbsolute": { "x": 80, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89
}
```

### Вызовы и авторизация:
- **Заголовок авторизации**: Входящий запрос авторизуется по токенам Service API, которые генерируются при публикации приложения.
- **Входные переменные**: Объявленные в `body`, `headers` или `params` поля автоматически извлекаются из соответствующих частей входящего HTTP-запроса и валидируются.

---

## 3. Plugin Trigger (`trigger-plugin`)

Запускает workflow при наступлении событий внутри установленных плагинов (например, "получено новое сообщение в Telegram").

### Структура в DSL

```json
{
  "id": "plugin_trigger_id",
  "type": "custom",
  "data": {
    "title": "Telegram Message",
    "type": "trigger-plugin",
    "plugin_id": "telegram-connector",
    "provider_id": "telegram",
    "event_name": "on_new_message",
    "subscription_id": "sub-uuid-1234",
    "plugin_unique_identifier": "telegram-connector:latest",
    "event_parameters": {
      "chat_type": {
        "type": "constant",
        "value": "group"
      }
    }
  },
  "position": { "x": 80, "y": 282 },
  "positionAbsolute": { "x": 80, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89
}
```

---

## Outputs

Любой триггер делает свои полученные входные переменные доступными для последующих нод workflow.

Доступ снаружи:
```json
["webhook_trigger_id", "payload_text"]
["plugin_trigger_id", "message_content"]
```
