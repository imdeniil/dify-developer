# Iteration Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.
> Все примеры из реальных тестов.

## Что это

Нода-контейнер для обработки каждого элемента массива через вложенный sub-workflow.
Аналог `for item in array` — только на уровне нод.

## Базовая структура (DSL)

Iteration состоит из **трёх обязательных частей**:

1. **Контейнер** — внешняя нода с параметрами итерации
2. **iteration-start** — внутренняя служебная нода (точка входа в sub-workflow)
3. **Внутренние ноды** — sub-workflow обработки, с `parentId` = id контейнера

```json
// 1. Контейнер
{
  "id": "iter_id",
  "type": "custom",
  "data": {
    "title": "ProcessEach",
    "type": "iteration",
    "iterator_selector": ["source_node_id", "items"],
    "iterator_input_type": "array[string]",
    "output_selector": ["inner_code_id", "result"],
    "output_type": "array[string]",
    "is_parallel": false,
    "parallel_nums": 10,
    "error_handle_mode": "terminated",
    "flatten_output": false,
    "start_node_id": "istart_id"
  },
  "position": { "x": 720, "y": 242 },
  "positionAbsolute": { "x": 720, "y": 242 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 480,
  "height": 200,
  "zIndex": 1
}

// 2. iteration-start (внутренний, обязателен)
{
  "id": "istart_id",
  "type": "custom-iteration-start",
  "data": {
    "title": "",
    "type": "iteration-start",
    "isInIteration": true
  },
  "parentId": "iter_id",
  "position": { "x": 760, "y": 300 },
  "positionAbsolute": { "x": 760, "y": 300 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 60,
  "height": 60,
  "zIndex": 1002
}

// 3. Внутренняя Code нода
{
  "id": "inner_code_id",
  "type": "custom",
  "data": {
    "title": "ProcessItem",
    "type": "code",
    "isInIteration": true,
    "isInLoop": false,
    "iteration_id": "iter_id",
    "variables": [
      { "variable": "item",  "value_selector": ["iter_id", "item"] },
      { "variable": "index", "value_selector": ["iter_id", "index"] }
    ],
    "code_language": "python3",
    "code": "def main(item: str, index: int) -> dict:\n    return {'result': f'{index}:{item.upper()}'}",
    "outputs": {
      "result": { "type": "string", "children": null }
    }
  },
  "parentId": "iter_id",
  "position": { "x": 880, "y": 282 },
  "positionAbsolute": { "x": 880, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89,
  "zIndex": 1002
}
```

## Ключевые поля контейнера

| Поле | Тип | Описание |
|------|-----|---------|
| `iterator_selector` | `[node_id, var_name]` | Источник массива |
| `iterator_input_type` | string | Тип элементов: `"array[string]"`, `"array[object]"`, `"array[number]"` |
| `output_selector` | `[inner_node_id, var_name]` | Какой output каждой итерации собирать |
| `output_type` | string | Тип выходного массива: `"array[string]"` и т.д. |
| `is_parallel` | boolean | `false` = sequential, `true` = parallel |
| `parallel_nums` | number | Кол-во параллельных потоков (max 10) |
| `error_handle_mode` | string | `"terminated"`, `"continue-on-error"`, `"remove-abnormal-output"` |
| `flatten_output` | boolean | Разгладить вложенные массивы (обычно `false`) |
| `start_node_id` | string | ID iteration-start ноды |

## Доступные переменные внутри Iteration

```python
# Через value_selector в inner nodes:
["iter_id", "item"]   # текущий элемент
["iter_id", "index"]  # индекс, 0-based
```

```python
# В Python коде:
def main(item: str, index: int) -> dict:
    # item  — текущий элемент ('apple', 'banana', ...)
    # index — порядковый номер (0, 1, 2, ...)
    return {"result": f"{index}:{item.upper()}"}
```

## Получение результата iteration снаружи

```json
// В inner ноде:
"output_selector": ["inner_code_id", "result"]

// Снаружи iteration, value_selector:
["iter_id", "output"]   // массив всех результатов
```

**Реальный тест (верифицировано):**
```python
# input:  ['apple', 'banana', 'cherry']
# inner:  f'{index}:{item.upper()}'
# output: ['0:APPLE', '1:BANANA', '2:CHERRY']
```

## Edges — правильная структура

```json
// Вход в iteration
{
  "source": "source_node_id",
  "sourceHandle": "source",
  "target": "iter_id",
  "targetHandle": "target",
  "data": { "isInIteration": false, "sourceType": "custom", "targetType": "iteration" }
}

// Выход из iteration
{
  "source": "iter_id",
  "sourceHandle": "source",
  "target": "next_node_id",
  "targetHandle": "target",
  "data": { "isInIteration": false, "sourceType": "iteration", "targetType": "custom" }
}

// Внутренние edges (istart → inner nodes)
{
  "source": "istart_id",
  "sourceHandle": "source",
  "target": "inner_code_id",
  "targetHandle": "target",
  "data": { "isInIteration": true, "iteration_id": "iter_id", "sourceType": "iteration-start", "targetType": "code" },
  "zIndex": 1002
}
```

## Error handling — верифицированные режимы

### terminated (default) ✅
Первая ошибка останавливает всю iteration.
```json
"error_handle_mode": "terminated"
```

### continue-on-error ✅ VERIFIED
Ошибочные элементы заменяются `None`, iteration продолжается.
```json
"error_handle_mode": "continue-on-error"
```
Реальный результат: `['GOOD', None, 'ALSO_GOOD']` (3 элемента, None вместо ошибки)

### remove-abnormal-output ✅ VERIFIED
> ⚠️ **Правильное значение enum: `"remove-abnormal-output"`** (не `"remove-abnormal"`).
> Неверное значение вызывает тихий validation error в worker — SSE не приходит вообще.

```json
"error_handle_mode": "remove-abnormal-output"
```
Реальный результат: `['OK', 'OK2']` (2 элемента, fail удалён из массива)

## Типы input и работа с объектами

### array[string] (верифицировано ✅)
```python
"iterator_input_type": "array[string]"
# item: строка, item.upper() работает напрямую
```

### array[object] (верифицировано ✅)
```python
"iterator_input_type": "array[object]"

def main(item, index: int) -> dict:
    name = item.get("name", "?")   # item — это dict
    age = item.get("age", 0)
    return {"result": f"{name} is {age} years old"}
# Реальный результат: "Alice is 30 years old | Bob is 25 years old"
```

### array[number]
```python
"iterator_input_type": "array[number]"
# item: число, работает арифметика напрямую
```

## Параллельный режим (верифицировано ✅)

```json
{
  "is_parallel": true,
  "parallel_nums": 5
}
```

- Элементы обрабатываются одновременно (до `parallel_nums` штук)
- Порядок результатов может не совпадать с порядком input
- Работает корректно, быстрее sequential для независимых задач

## Рабочий паттерн — полный граф

```python
# 1. Source node — создаёт массив
def main() -> dict:
    return {"items": ["apple", "banana", "cherry"]}

# 2. Inner Code — обрабатывает каждый элемент
def main(item: str, index: int) -> dict:
    return {"result": f"{index}:{item.upper()}"}

# 3. Collect Code — обрабатывает массив результатов
def main(results: list) -> dict:
    return {
        "joined": " | ".join(results),
        "count": len(results)
    }

# Финальный output: "0:APPLE | 1:BANANA | 2:CHERRY", count=3
```

## Важные тонкости

1. **`parentId`** — все внутренние ноды должны иметь `"parentId": "iter_id"`
2. **`zIndex: 1002`** — внутренние ноды и edges должны иметь этот zIndex
3. **`type: "custom-iteration-start"`** — iteration-start имеет другой тип, не `"custom"`
4. **`iteration_id`** в data внутренних нод — ID контейнера
5. **Output нода** внутри iteration — НЕ нужна. Только inner code нода; output_selector указывает что собирать
6. **Внешние переменные** НЕ доступны напрямую внутри iteration без явной передачи через `variables`

## Передача внешних переменных в Iteration

```json
// В inner node, variables:
[
  { "variable": "item",       "value_selector": ["iter_id", "item"] },
  { "variable": "index",      "value_selector": ["iter_id", "index"] },
  { "variable": "api_token",  "value_selector": ["env", "API_TOKEN"] },
  { "variable": "prefix",     "value_selector": ["start", "prefix_input"] }
]

// В Python:
def main(item: str, index: int, api_token: str, prefix: str) -> dict:
    return {"result": f"{prefix}_{index}_{item}"}
```
