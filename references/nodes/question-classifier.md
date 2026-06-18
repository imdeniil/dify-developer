# Question Classifier Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.
> Все примеры из реальных тестов.

## Что это

Нода для классификации пользовательского ввода по категориям (классам) с помощью LLM. Каждому классу соответствует отдельная ветка исполнения (edge) в графе workflow.

## Базовая структура (DSL)

```json
{
  "id": "classifier_id",
  "type": "custom",
  "data": {
    "title": "Classifier",
    "type": "question-classifier",
    "query_variable_selector": ["start_node_id", "query"],
    "model": {
      "provider": "imdeniil/zai-coding-plan/zai_coding_plan",
      "name": "glm-4.7-flash",
      "mode": "chat",
      "completion_params": {
        "temperature": 0.1
      }
    },
    "classes": [
      {
        "id": "class_weather",
        "name": "Weather questions",
        "label": "Weather"
      },
      {
        "id": "class_math",
        "name": "Math questions",
        "label": "Math"
      },
      {
        "id": "class_other",
        "name": "Other questions",
        "label": "Other"
      }
    ],
    "instruction": "Classify user query.",
    "memory": null,
    "vision": { "enabled": false }
  },
  "position": { "x": 400, "y": 282 },
  "positionAbsolute": { "x": 400, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89
}
```

## Outputs

Нода возвращает:
- `class_name` (string) — `name` сработавшего класса (например, `"Weather questions"`).
- `class_label` (string) — `label` сработавшего класса (например, `"Weather"`).
- `class_id` (string) — `id` сработавшего класса (например, `"class_weather"`).
- `usage` (object) — статистика токенов.

Доступ снаружи:
```json
["classifier_id", "class_name"]
["classifier_id", "class_label"]
["classifier_id", "class_id"]
```

---

## Настройка классов (Classes)

Каждый класс в списке `classes` должен иметь:
- `id` — уникальный строковый идентификатор. Используется в графе для подключения исходящих связей (edges) в поле `sourceHandle`.
- `name` — смысловое описание класса для LLM (например: "Вопросы про погоду и температуру").
- `label` — человекочитаемое название для UI.

---

## Edges и маршрутизация (Routing)

Для создания ветвления на основе классификации, исходящие связи (edges) должны использовать `sourceHandle`, равный `id` соответствующего класса.

### Пример описания связей в DSL:

```json
[
  // Ветка погоды
  {
    "id": "edge-weather",
    "source": "classifier_id",
    "sourceHandle": "class_weather",   // Должен совпадать с id класса!
    "target": "weather_handler_id",
    "targetHandle": "target",
    "data": {
      "isInIteration": false,
      "sourceType": "question-classifier",
      "targetType": "custom"
    }
  },
  // Ветка математики
  {
    "id": "edge-math",
    "source": "classifier_id",
    "sourceHandle": "class_math",      // Должен совпадать с id класса!
    "target": "math_handler_id",
    "targetHandle": "target",
    "data": {
      "isInIteration": false,
      "sourceType": "question-classifier",
      "targetType": "custom"
    }
  }
]
```

---

## Верификация на практике (T-10) ✅

В ходе реальных тестов на Dify 1.14.2 были отправлены следующие запросы:

1. **"Will it rain tomorrow?"**
   - Выход `class_id`: `"class_weather"`
   - Маршрутизация: Успешно перенаправлено на ветку `EndWeather` ✅

2. **"What is 15 * 6?"**
   - Выход `class_id`: `"class_math"`
   - Маршрутизация: Успешно перенаправлено на ветку `EndMath` ✅

3. **"Who was Albert Einstein?"**
   - Выход `class_id`: `"class_other"`
   - Маршрутизация: Успешно перенаправлено на ветку `EndOther` ✅

**Вывод**: Нода работает абсолютно стабильно. Логика ветвления в рантайме Dify базируется на значении `edge_source_handle`, которое заполняется результатом классификации.
