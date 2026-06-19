> ⚠️ ИСТОЧНИК ИСТИНЫ: Pydantic-схема в бэкенде Dify (в пакете graphon.nodes (в entities.py для code)).
> Если референс расходится с кодом — код прав. Перед генерацией DSL сверяй поля.

# Code Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.
> Все примеры — из реальных тестов, не из документации.

## Что это

Нода для выполнения Python 3.11 или JavaScript кода. Запускается в изолированном sandbox.

## Базовая структура (DSL)

```json
{
  "id": "code_node_id",
  "type": "custom",
  "data": {
    "title": "My Code",
    "type": "code",
    "variables": [
      {
        "variable": "input_name",
        "value_selector": ["source_node_id", "output_var"]
      }
    ],
    "code_language": "python3",
    "code": "def main(input_name: str) -> dict:\n    return {'result': input_name.upper()}",
    "outputs": {
      "result": { "type": "string", "children": null }
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

## Python — функция main()

```python
# Сигнатура — ОБЯЗАТЕЛЬНА
def main(arg1: str, arg2: list, arg3: int) -> dict:
    # ... логика ...
    return {
        "result": "value",    # должно совпадать с outputs декларацией
        "count": 42
    }
```

**Важно:**
- Функция **обязательно** называется `main`
- Возвращает **dict** — ключи должны совпадать с задекларированными `outputs`
- Если ключ объявлен в outputs но отсутствует в return — нода **упадёт** с `Output X is missing`

## Output типы — верифицированные

| Тип | Пример значения | Работает |
|-----|----------------|----------|
| `string` | `"hello"` | ✅ |
| `number` | `42`, `3.14` | ✅ |
| `boolean` | `True/False` | ✅ |
| `object` | `{"key": "val"}` | ✅ |
| `array[string]` | `["a", "b", "c"]` | ✅ |
| `array[number]` | `[1, 2, 3]` | ✅ |
| `array[object]` | `[{"k": "v"}]` | ✅ (объекты должны быть dict, не list!) |
| `array[array[*]]` | `[["a","b"], ["c"]]` | ❌ **ЛОМАЕТСЯ** |

### Array of arrays — подтверждённая ошибка

```python
# ❌ НЕ РАБОТАЕТ
def main() -> dict:
    return {"matrix": [["a", "b"], ["c", "d"]]}
# Ошибка: Output matrix[0] is not an object, got <class 'list'> instead at index 0.

# ✅ ОБХОДНОЕ РЕШЕНИЕ — JSON strings
import json
def main() -> dict:
    matrix = [["a", "b"], ["c", "d"]]
    return {"matrix_json": json.dumps(matrix)}
# Затем в следующей ноде: json.loads(matrix_json)
```

## Лимиты — верифицированные

| Утверждение | Реальность |
|-------------|-----------|
| Array limit 30 элементов | ❌ **НЕТ лимита** — тест с 500 элементами прошёл |
| Max object depth 5 | Не тестировалось (из официальной доки) |
| String max 80,000 chars | Не тестировалось (из официальной доки) |
| Numbers: -999999999 to 999999999 | Не тестировалось |

## Sandbox — доступные пакеты

**Протестировано на Dify 1.14.2:**

### Сторонние пакеты (доступны)
```python
import httpx      # ✅ HTTP клиент + ДЕЛАЕТ ВНЕШНИЕ ЗАПРОСЫ
import requests   # ✅ HTTP клиент + делает внешние запросы
import urllib3    # ✅
import hashlib    # ✅ (также есть в stdlib)
```

### Сторонние пакеты (НЕ доступны)
```
numpy, pandas, scipy, PIL (Pillow), bs4 (BeautifulSoup),
lxml, yaml (PyYAML), toml, aiohttp, httplib2,
openai, anthropic, tiktoken,
redis, psycopg2, pymongo,
cryptography, jwt (PyJWT),
boto3, google-cloud, azure
```

### Python Stdlib (всё работает)
```python
import json       # ✅
import re         # ✅
import datetime   # ✅
import math       # ✅
import random     # ✅
import hashlib    # ✅
import base64     # ✅
import os         # ✅ (импортируется, но filesystem ограничен sandbox)
import sys        # ✅
import subprocess # ✅ (импортируется, реальное выполнение не тестировалось)
```

## Сетевые запросы из sandbox

> ⚠️ Официальная дока Dify говорит что сетевые запросы заблокированы — **это НЕ ВЕРНО для self-hosted**.

**Верифицировано:** `httpx` и `requests` делают реальные HTTP запросы наружу.

```python
# ✅ РАБОТАЕТ в self-hosted Dify 1.14.2
def main() -> dict:
    import httpx
    r = httpx.get("https://api.example.com/data", timeout=10)
    return {"status": r.status_code, "body": r.text[:500]}

# ✅ Тоже работает
def main() -> dict:
    import requests
    r = requests.get("https://api.example.com/data", timeout=10)
    return {"status": r.status_code}

# ⚠️ urllib — проблемы с SSL cert verification
# import urllib.request
# urllib.request.urlopen(...)  → SSL: CERTIFICATE_VERIFY_FAILED
# Используй httpx или requests вместо urllib
```

**Важно для Docker:** URL'ы должны быть внешними или через внутренний Docker network:
- `http://api:5001/...` — внутренний Dify API
- `http://nginx:3006/...` — через nginx
- ❌ `http://localhost:3006/...` — не работает из sandbox

## Доступ к Environment Variables

```python
# В DSL — передать env var как input variable:
"variables": [
    {
        "variable": "my_secret",
        "value_selector": ["env", "MY_SECRET_VAR"]
    }
]

# В коде — получить как обычный аргумент:
def main(my_secret: str) -> dict:
    return {"has_secret": len(my_secret) > 0}
```

## Рабочие паттерны

### Паттерн 1: Условная HTTP отправка (замена If-Else + HTTP node)

```python
def main(data: str, should_send: bool, bot_token: str, chat_id: str) -> dict:
    import httpx
    result = {"sent": False}
    if should_send:
        r = httpx.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": data},
            timeout=15
        )
        result["sent"] = r.status_code == 200
        result["status"] = r.status_code
    return result
```

### Паттерн 2: JSON сериализация для передачи сложных структур

```python
import json

def main(items: list) -> dict:
    # Разбить на chunks и сериализовать (обход ограничения array[array])
    chunk_size = 10
    chunks = [items[i:i+chunk_size] for i in range(0, len(items), chunk_size)]
    return {
        "chunks_json": json.dumps(chunks, ensure_ascii=False),
        "total": len(items),
        "chunk_count": len(chunks)
    }

# В следующей ноде внутри Iteration:
# def main(chunk_json: str) -> dict:
#     chunk = json.loads(chunk_json)
#     ...
```

### Паттерн 3: Дата/время расчёты

```python
from datetime import datetime, timedelta, timezone

def main() -> dict:
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    return {
        "today": now.strftime("%Y-%m-%d"),
        "yesterday": yesterday.strftime("%Y-%m-%d"),
        "timestamp": int(now.timestamp())
    }
```

### Паттерн 4: Парсинг и фильтрация

```python
import re, json

def main(raw_text: str, min_length: int) -> dict:
    # Извлечь URLs
    urls = re.findall(r'https?://[^\s]+', raw_text)
    # Фильтровать
    filtered = [u for u in urls if len(u) >= min_length]
    return {
        "urls": filtered,
        "count": len(filtered),
        "summary": f"Found {len(filtered)} URLs"
    }
```

## Известные ошибки и их смысл

| Ошибка | Причина |
|--------|---------|
| `Output X is missing` | return dict не содержит ключ X, объявленный в outputs |
| `Output X[0] is not an object, got <class 'list'>` | Пытаешься вернуть array of arrays |
| `Output error is missing` (или любой ключ) | Один из путей кода не возвращает все объявленные поля |
| Node timeout | Бесконечный цикл или слишком долгий HTTP запрос |

## JavaScript поддержка

```javascript
// Базовая структура
function main(items) {
    const processed = items.map(item => item.toUpperCase());
    return { result: processed };
}

// Доступно: стандартные JS объекты (Array, Object, String, Math, JSON, Date)
// Не доступно: fetch, XMLHttpRequest, require внешних пакетов (неверифицировано)
```

## DSL — outputs декларация

```json
"outputs": {
  "my_string":  { "type": "string",        "children": null },
  "my_number":  { "type": "number",        "children": null },
  "my_bool":    { "type": "boolean",       "children": null },
  "my_object":  { "type": "object",        "children": null },
  "my_arr_str": { "type": "array[string]", "children": null },
  "my_arr_num": { "type": "array[number]", "children": null },
  "my_arr_obj": { "type": "array[object]", "children": null }
}
```

`children: null` — **обязателен** для всех типов, даже scalar.
