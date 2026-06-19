> ⚠️ ИСТОЧНИК ИСТИНЫ: Pydantic-схема в бэкенде Dify (в пакете graphon.nodes (в entities.py для start)).
> Если референс расходится с кодом — код прав. Перед генерацией DSL сверяй поля.

# Start Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.

## Что это

Начальная нода (`start`), являющаяся точкой входа в workflow. Описывает входные переменные, которые приложение ожидает получить от пользователя или API при запуске.

## Базовая структура (DSL)

```json
{
  "id": "start_node_id",
  "type": "custom",
  "data": {
    "title": "Start",
    "type": "start",
    "variables": [
      {
        "variable": "query",
        "type": "text-input",
        "required": true,
        "label": "Query"
      },
      {
        "variable": "max_results",
        "type": "number",
        "required": false,
        "label": "Max Results"
      }
    ]
  },
  "position": { "x": 80, "y": 282 },
  "positionAbsolute": { "x": 80, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89
}
```

## Доступные типы переменных (Variable Entity Types)

В Dify v1.14.2 поддерживаются следующие типы переменных на входе:

| Тип в DSL (`type`) | Описание | Ожидаемый тип данных |
|---------------------|----------|----------------------|
| `text-input` | Короткая текстовая строка | `string` |
| `paragraph` | Длинный текст (абзац) | `string` |
| `select` | Выпадающий список вариантов | `string` (одно из значений) |
| `number` | Числовое поле | `int` / `float` |
| `file` | Одиночный файл | `object` (метаданные файла) |
| `file-list` | Список файлов | `array` (массив метаданных файлов) |

## Outputs

Каждая описанная в `variables` переменная становится выходным параметром ноды `start`.

Доступ снаружи (в селекторах других нод):
```json
["start_node_id", "query"]
["start_node_id", "max_results"]
```

---

## ⚠️ Критические особенности валидации (T-21) ✅

1. **Обязательное наличие поля `label`**:
   При парсинге схемы `StartNodeData` Pydantic-валидатор в Dify строго требует наличия поля `"label"` для каждой переменной. Если передать переменную без ярлыка (label), workflow не сохранится и вернёт ошибку валидации.
   ```json
   // ❌ Вызовет ValidationError:
   {"variable": "query", "type": "text-input", "required": true}

   // ✅ Правильный формат:
   {"variable": "query", "type": "text-input", "required": true, "label": "Query"}
   ```

2. **Единственность ноды**:
   В любом workflow/chatflow может быть строго **одна** нода типа `start`.
