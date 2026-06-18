# Tool Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.

## Что это

Нода инструмента (`tool`) позволяет вызывать внешние и встроенные функции прямо в процессе выполнения workflow. Это могут быть поисковые системы, калькуляторы, API сторонних систем, Model Context Protocol (MCP) сервисы или другие workflow-приложения, оформленные как инструменты.

## Типы провайдеров (`provider_type`)

В Dify v1.14.2 поддерживаются следующие типы провайдеров инструментов:

1. `builtin` — Встроенные системные инструменты (например, `time` для получения даты, `webscraper`, `wikipedia` и т.д.).
2. `custom` — Пользовательские инструменты, созданные через импорт OpenAPI/Swagger схем.
3. `workflow` — Использование другого сохранённого workflow как инструмента (Workflow-as-a-Tool).
4. `mcp` — Инструменты от внешних серверов по протоколу Model Context Protocol (через HTTP-транспорты).

## Базовая структура версии 2 (DSL)

В актуальной версии Dify используется версия 2 ноды инструментов (`tool_node_version: "2"`).

```json
{
  "id": "tool_node_id",
  "type": "custom",
  "data": {
    "title": "TimeTool",
    "type": "tool",
    "provider_id": "time",
    "provider_type": "builtin",
    "provider_name": "time",
    "tool_name": "current_time",
    "tool_label": "Current Time",
    "tool_configurations": {},
    "tool_node_version": "2",
    "tool_parameters": {
      "format": {
        "type": "constant",
        "value": "%Y-%m-%d"
      },
      "timezone": {
        "type": "constant",
        "value": "UTC"
      }
    }
  },
  "position": { "x": 400, "y": 282 },
  "positionAbsolute": { "x": 400, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89
}
```

## Параметры ноды

- `provider_id` (string) — уникальный ID провайдера.
- `provider_type` (string) — один из типов: `builtin`, `custom`, `workflow`, `mcp`.
- `provider_name` / `tool_name` (string) — системные имена провайдера и самого инструмента.
- `tool_label` (string) — человекочитаемое имя инструмента (отображается в UI).
- `tool_configurations` (object) — глобальные настройки авторизации или конфиг провайдера (если требуются).
- `tool_node_version` (string) — всегда `"2"`.
- `tool_parameters` (object) — параметры вызова инструмента. Каждое свойство внутри описывает тип источника данных:
  - `"type": "constant"` — значение передается как константа в `"value"`.
  - `"type": "variable"` — значение извлекается динамически из переменной по селектору в `"value"` (например, `["start", "query"]`).
  - `"type": "mixed"` — шаблонизированная строка со вставками переменных.

## Outputs

Большинство инструментов возвращают стандартный набор выходов:
- `text` (string) — текстовый ответ (или markdown представление).
- `json` (array/object) — структурированный ответ в формате JSON.
- `files` (array) — список сгенерированных файлов или медиа-объектов.

Доступ снаружи:
```json
["tool_node_id", "text"]
["tool_node_id", "json"]
```

---

## ⚠️ Критические особенности валидации (T-20) ✅

1. **Обязательность полей `tool_label` и `tool_configurations`**:
   При синхронизации черновика workflow Dify бэкенд производит строгую валидацию схемы `ToolEntity`. Отсутствие `"tool_label"` или `"tool_configurations"` вызывает мгновенный сбой Pydantic-валидации в Celery worker (`ValidationError: ToolEntity`):
   ```json
   // ❌ Приведет к ошибке валидации:
   "data": {
     "type": "tool",
     "tool_name": "current_time"
   }

   // ✅ Правильно:
   "data": {
     "type": "tool",
     "tool_name": "current_time",
     "tool_label": "Current Time",
     "tool_configurations": {}
   }
   ```

2. **Формат параметров**:
   Нельзя передавать параметры инструмента напрямую как простые значения ключ-значение. Их обязательно нужно оборачивать в объект с `"type"` и `"value"` для корректной типизации в v2.
