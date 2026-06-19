> ⚠️ ИСТОЧНИК ИСТИНЫ: Pydantic-схема в бэкенде Dify (в ~/dify/api/core/workflow/nodes/agent/entities.py).
> Если референс расходится с кодом — код прав. Перед генерацией DSL сверяй поля.

# Agent Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.

## Что это

Нода агента (`agent`) позволяет интегрировать в структуру workflow автономных ИИ-агентов. Агент самостоятельно принимает решения, планирует действия и вызывает доступные инструменты (используя ReAct или Function Calling) для достижения поставленной цели.

## Две версии ноды агента

В Dify v1.14.2 сосуществуют две принципиально разные архитектуры реализации агентов:

---

### Версия 1: Plugin-based Agent (v1)

Агент настраивается непосредственно внутри ноды workflow с использованием стратегий-плагинов.

#### Базовая структура v1 (DSL)

```json
{
  "id": "agent_v1_id",
  "type": "custom",
  "data": {
    "title": "Agent Node V1",
    "type": "agent",
    "agent_strategy_provider_name": "plugin_id/provider_name",
    "agent_strategy_name": "react",
    "agent_strategy_label": "ReAct Strategy",
    "tool_node_version": "2",
    "agent_parameters": {
      "query": {
        "type": "variable",
        "value": ["start", "query"]
      },
      "model": {
        "type": "constant",
        "value": {
          "provider": "imdeniil/zai-coding-plan/zai_coding_plan",
          "name": "glm-4.7-flash"
        }
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

#### Параметры v1:
- `agent_strategy_provider_name` (string) — название плагина-провайдера, предоставляющего агентские возможности.
- `agent_strategy_name` (string) — идентификатор стратегии (например, `"react"` или `"function_calling"`).
- `agent_parameters` (object) — параметры, передаваемые на вход стратегии (модель, системный промпт, инструменты, пользовательский запрос).

> ⚠️ В self-hosted инсталляциях Dify без установленных плагинов агентов список плагинов-стратегий по умолчанию может быть пустым (`[]`), что делает использование ноды версии 1 невозможным без предварительной установки плагина из маркетплейса.

---

### Версия 2: App-bound Agent (v2)

Агент связывается с отдельным самостоятельным ИИ-приложением типа "Agent App", созданным и настроенным в панели Dify (Studio).

#### Базовая структура v2 (DSL)

```json
{
  "id": "agent_v2_id",
  "type": "custom",
  "data": {
    "title": "Agent Node V2",
    "type": "agent",
    "version": "2",
    "agent_node_kind": "dify_agent"
  },
  "position": { "x": 400, "y": 282 },
  "positionAbsolute": { "x": 400, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89
}
```

#### Параметры v2:
- `version` (string) — строго `"2"`.
- `agent_node_kind` (string) — строго `"dify_agent"`.

---

## Outputs

Нода `agent` возвращает:
- `text` (string) — итоговый текстовый ответ, сформированный агентом.

Доступ снаружи:
```json
["agent_node_id", "text"]
```

---

## ⚠️ Критические особенности и ограничения версии 2 (T-22) ✅

1. **Необходимость внешней привязки (Database Binding)**:
   В отличие от большинства других нод Dify, которые полностью переносятся через DSL-граф, нода `agent` версии 2 **не является автономной**. При запуске workflow Dify ищет привязанного агента в таблице базы данных `workflow_agent_node_bindings` по ключу `(tenant_id, app_id, workflow_id, node_id)`.
   
2. **Сбой при динамическом тестировании (Draft Run API)**:
   При отправке и выполнении сырого JSON-графа через API запуска черновиков (`/workflows/draft/run`), если вы динамически создали `node_id` агента версии 2, но не создали запись привязки в БД через специальные API-ручки (`composer_service` / `roster_service`), выполнение графа мгновенно упадет или зависнет с ошибкой:
   `WorkflowAgentBindingError: agent_binding_not_found` (Связь агента для ноды не найдена).
