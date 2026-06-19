> ⚠️ ИСТОЧНИК ИСТИНЫ: Pydantic-схема в бэкенде Dify (в пакете graphon.nodes (в entities.py для if_else)).
> Если референс расходится с кодом — код прав. Перед генерацией DSL сверяй поля.

# If-Else Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.

## Что это

Условное ветвление workflow. Поддерживает несколько именованных кейсов (cases) плюс
обязательная ветка `false` (else). Работает надёжно — утверждение старого reference
о "500 в сложных графах" **не подтвердилось**.

## Базовая структура (DSL)

```json
{
  "id": "if_node_id",
  "type": "custom",
  "data": {
    "title": "Check Condition",
    "type": "if-else",
    "cases": [
      {
        "case_id": "my_case_name",
        "logical_operator": "and",
        "conditions": [
          {
            "comparison_operator": ">",
            "value": "10",
            "variable_selector": ["code_node_id", "count"],
            "varType": "number"
          }
        ]
      }
    ]
  },
  "position": { "x": 720, "y": 282 },
  "positionAbsolute": { "x": 720, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89
}
```

## Outputs if-else ноды

If-else нода сама экспонирует:
- `result` — boolean (true/false)
- `selected_case_id` — id сработавшего кейса или "false"

```python
# Доступ в следующих нодах:
value_selector: ["if_node_id", "result"]           # boolean
value_selector: ["if_node_id", "selected_case_id"] # string
```

## Edges — как правильно подключать ветки

```json
{
  "source": "if_node_id",
  "sourceHandle": "my_case_name",  // case_id для true-ветки
  "target": "end_node_id",
  "targetHandle": "target"
}

{
  "source": "if_node_id",
  "sourceHandle": "false",         // ВСЕГДА "false" для else-ветки
  "target": "end_else_id",
  "targetHandle": "target"
}
```

**Важно**: `sourceHandle` = `case_id` для каждой named ветки, `"false"` для else.

## Comparison operators — полный верифицированный список

Из реального error message Dify при передаче неверного оператора:

### Строки (string)
```
contains        — содержит подстроку
not contains    — не содержит
start with      — начинается с
end with        — заканчивается на
is              — точное совпадение (или boolean true/false)
is not          — не равно
empty           — пустая строка
not empty       — непустая строка
in              — входит в список
not in          — не входит в список
```

### Числа (number)
```
=               — равно (Unicode =)
≠               — не равно (Unicode ≠, НЕ "!=")
>               — больше (НЕ "greater-than"!)
<               — меньше (НЕ "less-than"!)
≥               — больше или равно (Unicode ≥)
≤               — меньше или равно (Unicode ≤)
```

### Любые типы
```
null            — значение null/None
not null        — не null
exists          — переменная существует
not exists      — переменная не существует
all of          — все элементы массива удовлетворяют условию
```

> ⚠️ **Критично**: числовые операторы — это Unicode символы `>`, `<`, `≥`, `≤`, `=`, `≠`.
> Строки `"greater-than"`, `"less-than"`, `"equal"` и т.д. **НЕ работают** → validation error.

## varType — типы переменных в условиях

```
"varType": "string"   — строка
"varType": "number"   — число
"varType": "boolean"  — булево
"varType": "array"    — массив
```

## logical_operator

```
"logical_operator": "and"   — все условия должны быть true
"logical_operator": "or"    — хотя бы одно условие true
```

## Рабочий пример — несколько кейсов (верифицировано)

```json
{
  "type": "if-else",
  "cases": [
    {
      "case_id": "long_with_e",
      "logical_operator": "and",
      "conditions": [
        {
          "comparison_operator": ">",
          "value": "4",
          "variable_selector": ["code_id", "length"],
          "varType": "number"
        },
        {
          "comparison_operator": "is",
          "value": "true",
          "variable_selector": ["code_id", "has_e"],
          "varType": "boolean"
        }
      ]
    },
    {
      "case_id": "just_long",
      "logical_operator": "and",
      "conditions": [
        {
          "comparison_operator": ">",
          "value": "4",
          "variable_selector": ["code_id", "length"],
          "varType": "number"
        }
      ]
    }
  ]
}
```

**Реальный результат тестов:**
```
'hello' (len=5, has_e=True)  → EndLongE  ✅
'world' (len=5, has_e=False) → EndLong   ✅
'hi'    (len=2, has_e=False) → EndShort  ✅
```

## Boolean условия (верифицировано)

```json
{
  "comparison_operator": "is",
  "value": "true",
  "variable_selector": ["code_id", "flag"],
  "varType": "boolean"
}
```

Значения: `"true"` или `"false"` (строки, не boolean).

## Простой пример — один кейс

```json
{
  "type": "if-else",
  "cases": [
    {
      "case_id": "is_big",
      "logical_operator": "and",
      "conditions": [
        {
          "comparison_operator": ">",
          "value": "100",
          "variable_selector": ["code_id", "count"],
          "varType": "number"
        }
      ]
    }
  ]
}
```

Edges:
- `sourceHandle: "is_big"` → ветка для count > 100
- `sourceHandle: "false"` → ветка для count ≤ 100

## Несколько End нод

Workflow с несколькими End нодами (по одной на ветку) работает нормально.
Каждая ветка if-else должна вести к своей End ноде.

## Утверждения из reference — результаты верификации

| Утверждение | Статус |
|-------------|--------|
| If-Else даёт 500 в сложных графах | ❌ **НЕВЕРНО** — работает стабильно |
| Нужно использовать Code node вместо If-Else | ❌ **НЕВЕРНО** — If-Else надёжен |
| `greater-than` как оператор | ❌ **НЕВЕРНО** — нужен символ `>` |
| Boolean через `is`/`"true"` | ✅ Верно |

## Когда использовать Code node вместо If-Else

If-Else достаточен для большинства случаев. Code node нужен только если:
- Нужна **условная HTTP отправка** (httpx внутри if) без лишних нод
- Условие слишком сложное для визуального конструктора
- Нужно более 10+ ветвлений (читаемость)
