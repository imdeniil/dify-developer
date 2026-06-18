# Variable Aggregator Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.

## Что это

Нода для **схождения параллельных веток** в одну переменную. Классический use-case:
if-else создаёт 2 ветки — каждая пишет в разные переменные — aggregator склеивает в одну.

## Базовая структура (DSL)

```json
{
  "id": "va_node_id",
  "type": "custom",
  "data": {
    "title": "Merge",
    "type": "variable-aggregator",
    "output_type": "string",
    "variables": [
      ["branch_a_node_id", "label"],
      ["branch_b_node_id", "label"]
    ],
    "advanced_settings": {
      "group_enabled": false,
      "groups": []
    }
  },
  "position": { "x": 1360, "y": 282 },
  "positionAbsolute": { "x": 1360, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89
}
```

> ⚠️ **`output_type` обязателен** на верхнем уровне. Без него — validation error в worker,
> workflow молча не запускается и SSE не приходит.

## Output

Одна переменная `output` — значение из той ветки, которая завершилась (остальные не выполнялись).

```json
["va_node_id", "output"]
```

## Поле variables — формат

```json
"variables": [
  ["node_a_id", "var_name_a"],
  ["node_b_id", "var_name_b"],
  ["node_c_id", "var_name_c"]
]
```

Каждый элемент — массив из 2 строк: `[node_id, variable_name]`.

## output_type — допустимые значения

Из кода `graphon/nodes/variable_aggregator/entities.py` — тип `SegmentType`:

```
"string"
"number"
"boolean"
"object"
"array[string]"
"array[number]"
"array[object]"
```

## Edges — targetType

```json
{
  "source": "branch_node_id",
  "sourceHandle": "source",
  "target": "va_node_id",
  "targetHandle": "target",
  "data": {
    "sourceType": "custom",
    "targetType": "variable-aggregator"
  }
}
```

```json
{
  "source": "va_node_id",
  "sourceHandle": "source",
  "target": "next_node_id",
  "targetHandle": "target",
  "data": {
    "sourceType": "variable-aggregator",
    "targetType": "custom"
  }
}
```

## Рабочий пример — if-else merge (верифицировано ✅)

```
Start(num) → Code(check) → If-Else → BigBranch → ┐
                                  ↘ SmallBranch → Aggregator → End
```

```python
# Code: check
def main(num: float) -> dict:
    return {"is_big": num > 50, "num": num}

# BigBranch (if is_big == true)
def main(num: float) -> dict:
    return {"label": f"BIG:{num}"}

# SmallBranch (else)
def main(num: float) -> dict:
    return {"label": f"SMALL:{num}"}
```

```json
{
  "output_type": "string",
  "variables": [
    ["big_branch_id", "label"],
    ["small_branch_id", "label"]
  ]
}
```

**Реальный результат:**
```
num=100 → output="BIG:100.0"   ✅
num=10  → output="SMALL:10.0"  ✅
```

## Group mode — advanced_settings

Для схождения переменных **разных типов** в именованные группы:

```json
{
  "output_type": "string",
  "variables": [],
  "advanced_settings": {
    "group_enabled": true,
    "groups": [
      {
        "output_type": "string",
        "variables": [["node_a_id", "text_var"]],
        "group_name": "group_a"
      },
      {
        "output_type": "number",
        "variables": [["node_b_id", "num_var"]],
        "group_name": "group_b"
      }
    ]
  }
}
```

В group mode каждая группа имеет отдельный `output_type` и `group_name`.
Доступ к выходу: `["va_id", "group_a"]`, `["va_id", "group_b"]`.

> ⚠️ Group mode не тестировался — поведение не верифицировано.

## Типичные ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| SSE не приходит, workflow молчит | Нет `output_type` в data | Добавь `"output_type": "string"` |
| `output` = null | Ни одна ветка не выполнялась | Проверь if-else routing |
| Validation error в worker logs | Неверный тип в output_type | Используй допустимые SegmentType значения |

## Когда использовать

| Сценарий | Aggregator | Альтернатива |
|----------|-----------|-------------|
| if-else → одна переменная дальше | ✅ | Code нода внутри каждой ветки (дублирование) |
| Параллельные ветки → единый output | ✅ | — |
| Нужны ОБА результата обеих веток | ❌ | Не применимо (только одна ветка выполняется) |
