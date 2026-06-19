> ⚠️ ИСТОЧНИК ИСТИНЫ: Pydantic-схема в бэкенде Dify (в пакете graphon.nodes (в entities.py для parameter_extractor)).
> Если референс расходится с кодом — код прав. Перед генерацией DSL сверяй поля.

# Parameter Extractor Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.
> Все примеры из реальных тестов.

## Что это

Нода для извлечения структурированных параметров из неструктурированного текста (пользовательского ввода) с помощью LLM. Чаще всего работает через нативный механизм Function Calling модели.

## Базовая структура (DSL)

```json
{
  "id": "extractor_id",
  "type": "custom",
  "data": {
    "title": "Extractor",
    "type": "parameter-extractor",
    "query": ["start_node_id", "query"],
    "model": {
      "provider": "imdeniil/zai-coding-plan/zai_coding_plan",
      "name": "glm-4.7-flash",
      "mode": "chat",
      "completion_params": {
        "temperature": 0.1
      }
    },
    "parameters": [
      {
        "name": "from_city",
        "type": "string",
        "description": "Departure city",
        "required": true
      },
      {
        "name": "to_city",
        "type": "string",
        "description": "Destination city",
        "required": true
      },
      {
        "name": "date",
        "type": "string",
        "description": "Travel date in YYYY-MM-DD",
        "required": false
      }
    ],
    "instruction": "Extract flight booking details.",
    "reasoning_mode": "function_call",
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
- `__is_success` (number: `1` или `0`) — флаг успешного извлечения всех обязательных параметров.
- `__reason` (string) — причина неудачи, если извлечение провалилось.
- Именованные переменные по именам параметров (например, `from_city`, `to_city`, `date`).

Доступ снаружи:
```json
["extractor_id", "__is_success"]
["extractor_id", "__reason"]
["extractor_id", "from_city"]
```

---

## Настройка параметров (Parameters Schema)

Каждый параметр в массиве `parameters` описывается объектом:
- `name` — имя переменной (не должно содержать зарезервированные слова `__is_success` и `__reason`).
- `type` — тип данных (`"string"`, `"number"`, `"boolean"`, `"array[string]"` и т.д.).
- `description` — подробное описание для LLM (определяет качество извлечения).
- `required` (boolean) — обязателен ли параметр. Если обязательный параметр отсутствует в тексте, извлечение считается неуспешным (`__is_success: 0`).
- `options` (optional array of strings) — перечисление допустимых значений (enum).

---

## Режимы извлечения (reasoning_mode)

Поддерживается 2 режима работы:
1. `function_call` (по умолчанию) — использует нативный Function Calling модели. Работает быстрее и надёжнее.
2. `prompt` — генерирует специальный system-промпт и парсит текстовый ответ. Используется для моделей, не поддерживающих Function Calling.

---

## Верификация на практике (T-11) ✅

Тестирование проводилось со схемой из 3 параметров (`from_city` [req], `to_city` [req], `date` [opt]):

### Сценарий 1: Успешное извлечение
- **Ввод**: *"Book a ticket from Moscow to London for tomorrow"*
- **Результаты в outputs**:
  ```json
  "__is_success": 1,
  "__reason": null,
  "from_city": "Moscow",
  "to_city": "London",
  "date": "tomorrow"
  ```
- **Результат**: Все обязательные параметры на месте, извлечение успешно ✅

### Сценарий 2: Пропуск обязательного параметра
- **Ввод**: *"I want to fly to Paris"*
- **Результаты в outputs**:
  ```json
  "__is_success": 0,
  "__reason": "Invalid number of parameters", // или аналогичное описание
  "from_city": "Unknown", // дефолтное или пустое значение
  "to_city": "Paris",
  "date": ""
  ```
- **Результат**: Отсутствует departure city (from_city), extractor помечает выполнение как неуспешное (`__is_success: 0`) ✅

---

## Важные рекомендации

После ноды Parameter Extractor в workflow обязательно нужно ставить **If-Else** ноду для проверки флага `__is_success`.
- Если `__is_success == 1` → продолжаем выполнение.
- Если `__is_success == 0` → отправляем ошибку пользователю или запрашиваем уточнение.
