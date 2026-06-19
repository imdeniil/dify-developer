> ⚠️ ИСТОЧНИК ИСТИНЫ: Pydantic-схема в бэкенде Dify (в пакете graphon.nodes (в entities.py для variable_assigner)).
> Если референс расходится с кодом — код прав. Перед генерацией DSL сверяй поля.

# Variable Assigner Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.

## Что это

Нода присвоения переменных (`assigner`) используется для изменения значений **разговорных переменных** (Conversation Variables) внутри сессии чата. Она позволяет накапливать контекст, вести подсчеты (счетчики) или собирать историю сообщений между шагами диалога.

## Версия 1 (v1)

Базовая версия ноды. Выполняет одну операцию записи над выбранной переменной.

### Базовая структура v1 (DSL)

```json
{
  "id": "assigner_v1_id",
  "type": "custom",
  "data": {
    "title": "Assigner V1",
    "type": "assigner",
    "assigned_variable_selector": ["conversation", "user_history"],
    "write_mode": "over-write",
    "input_variable_selector": ["start", "query"]
  },
  "position": { "x": 400, "y": 282 },
  "positionAbsolute": { "x": 400, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89
}
```

### Параметры v1:
- `assigned_variable_selector` (array) — путь к изменяемой переменной. Первая часть всегда `"conversation"`.
- `input_variable_selector` (array) — путь к переменной-источнику данных.
- `write_mode` (string) — режим записи. Доступные значения:
  - `"over-write"` — полная перезапись переменной.
  - `"append"` — добавление нового элемента в массив (если переменная является списком).
  - `"clear"` — очистка переменной.

---

## Версия 2 (v2)

Продвинутая версия ноды. Поддерживает выполнение нескольких операций в рамках одной ноды и расширенные операции над структурами данных (массивами, числами, словарями).

### Базовая структура v2 (DSL)

```json
{
  "id": "assigner_v2_id",
  "type": "custom",
  "data": {
    "title": "Assigner V2",
    "type": "assigner",
    "version": "2",
    "items": [
      {
        "variable_selector": ["conversation", "message_count"],
        "input_type": "constant",
        "operation": "+=",
        "value": 1
      },
      {
        "variable_selector": ["conversation", "topics_list"],
        "input_type": "variable",
        "operation": "append",
        "value": ["start", "query"]
      }
    ]
  },
  "position": { "x": 400, "y": 282 },
  "positionAbsolute": { "x": 400, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89
}
```

### Операции v2 (`operation`):

| Операция | Описание | Поддерживаемые типы данных |
|----------|----------|---------------------------|
| `"over-write"` | Полная перезапись значения | Любые |
| `"clear"` | Очистка значения (сброс в null/empty) | Любые |
| `"append"` | Добавление одного элемента в конец массива | Array |
| `"extend"` | Объединение двух массивов (добавление элементов) | Array |
| `"set"` | Установка значения по ключу в объекте | Object/Dictionary |
| `"+="` | Математическое сложение / инкремент | Number (Int/Float) |
| `"-="` | Математическое вычитание / декремент | Number (Int/Float) |
| `"*="` | Математическое умножение | Number (Int/Float) |
| `"/="` | Математическое деление | Number (Int/Float) |
| `"remove-first"`| Удаление первого элемента массива | Array |
| `"remove-last"` | Удаление последнего элемента массива | Array |

### Типы источника v2 (`input_type`):
- `"constant"` — значение берется непосредственно из поля `value` (литерал: строка, число, массив).
- `"variable"` — значение извлекается по селектору пути, переданному в `value` (например, `["start", "query"]`).

---

## Outputs

Нода `assigner` не создает новых выходных переменных в пуле данных для последующих шагов, так как ее единственная цель — изменение персистентных переменных разговора (`conversation`).

---

## ⚠️ Критические особенности и ограничения

1. **Только в Chatflow**:
   Нода `variable-assigner` работоспособна только в Chatflow приложениях. В обычных workflow-приложениях отсутствует объект `conversation`, поэтому попытка записи вызовет ошибку во время выполнения.
   
2. **Предварительное объявление переменных**:
   Вы не можете динамически создавать переменные во время выполнения. Все изменяемые переменные разговора должны быть заранее объявлены в параметрах черновика workflow (`conversation_variables` на уровне графа):
   ```json
   "conversation_variables": [
     {
       "id": "var_id",
       "name": "message_count",
       "type": "number",
       "value": 0
     }
   ]
   ```
