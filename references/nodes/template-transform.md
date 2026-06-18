# Template-Transform Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.
> Все примеры из реальных тестов.

## Что это

Нода для форматирования строк через **Jinja2** шаблонизатор.
Принимает переменные из других нод → рендерит текстовый output.

Используется когда нужно:
- Собрать текст из нескольких переменных
- Форматировать список в читаемый текст
- Применить фильтры к данным без Code ноды

## Базовая структура (DSL)

```json
{
  "id": "tmpl_node_id",
  "type": "custom",
  "data": {
    "title": "Format Output",
    "type": "template-transform",
    "variables": [
      { "variable": "items",  "value_selector": ["code_node_id", "items"] },
      { "variable": "count",  "value_selector": ["code_node_id", "count"] },
      { "variable": "name",   "value_selector": ["start", "user_name"] }
    ],
    "template": "Hello {{ name }}!\nYou have {{ count }} items:\n{% for item in items %}- {{ item }}\n{% endfor %}"
  },
  "position": { "x": 720, "y": 282 },
  "positionAbsolute": { "x": 720, "y": 282 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "width": 242,
  "height": 89
}
```

**Output:** единственная переменная `output` (string) — результат рендеринга.

Доступ из следующих нод: `value_selector: ["tmpl_node_id", "output"]`

## Jinja2 — верифицированные возможности

Все примеры протестированы реально на Dify 1.14.2:

### 1. Индексация массива ✅

```jinja2
{{ items[0] }}      {# первый элемент → "apple" #}
{{ items[-1] }}     {# последний → "cherry" #}
{{ items[1:] }}     {# slice → ["banana", "cherry"] #}
```

> ⚠️ **Reference старого агента утверждал что `items[0]` не работает — это НЕВЕРНО.**
> В `template-transform` Jinja2 indexing работает полностью.
> Путаница была с синтаксисом `{{#node.items[0]#}}` в HTTP body — там действительно не работает.

### 2. Цикл for ✅

```jinja2
{% for item in items %}
{{ loop.index }}. {{ item }}
{% endfor %}

{# Результат:
1. apple
2. banana
3. cherry
#}
```

`loop.index` — 1-based счётчик (не 0).
`loop.index0` — 0-based.

### 3. Условие if ✅

```jinja2
{% if enabled %}Active{% else %}Disabled{% endif %}

{% if count > 5 %}Many{% elif count > 0 %}Some{% else %}None{% endif %}
```

### 4. Фильтры ✅

```jinja2
{{ items | join(', ') }}        {# "apple, banana, cherry" #}
{{ items | length }}             {# 3 #}
{{ items[0] | upper }}          {# "APPLE" #}
{{ score | round(1) }}          {# 7.5 #}
{{ text | truncate(50) }}        {# обрезка #}
{{ value | default('N/A') }}    {# если переменная не задана #}
```

### 5. Математика ✅

```jinja2
{{ count * 2 }}       {# 6 #}
{{ count + 10 }}      {# 13 #}
{{ score / 2 }}       {# 3.75 #}
```

### 6. Default для отсутствующих переменных ✅

```jinja2
{{ missing_var | default('fallback') }}   {# "fallback" если переменной нет #}
```

Не вызывает ошибку — просто подставляет default.

### 7. Slice ✅

```jinja2
{{ items[1:] | join('+') }}    {# "banana+cherry" #}
{{ items[:2] }}                {# ["apple", "banana"] #}
```

## Рабочий пример — полный тест

```jinja2
{# Входные данные: items=["apple","banana","cherry"], count=3, score=7.5, enabled=True #}

1. Index: {{ items[0] }} / {{ items[-1] }}
2. Loop: {% for i in items %}{{ loop.index }}:{{ i }} {% endfor %}
3. If: {% if enabled %}YES{% else %}NO{% endif %}
4. Join: {{ items | join(', ') }}
5. Len: {{ items | length }}
6. Upper: {{ items[0] | upper }}
7. Math: {{ count * 2 }}
8. Default: {{ missing | default('N/A') }}
9. Slice: {{ items[1:] | join('+') }}
10. Round: {{ score | round(1) }}
```

**Реальный output:**
```
1. Index: apple / cherry
2. Loop: 1:apple 2:banana 3:cherry 
3. If: YES
4. Join: apple, banana, cherry
5. Len: 3
6. Upper: APPLE
7. Math: 6
8. Default: N/A
9. Slice: banana+cherry
10. Round: 7.5
```

## Ограничения

| Ограничение | Статус |
|-------------|--------|
| Нет доступа к внешним данным (HTTP, DB) | ✅ — только переменные из workflow |
| Нет import Python модулей | ✅ — это шаблонизатор, не код |
| Output всегда `string` | ✅ — если нужно число/array, используй Code ноду |
| `{{#node.var[0]#}}` синтаксис не работает | ✅ — этот синтаксис для HTTP body, не для Jinja2 |

## Когда использовать vs Code нода

| Задача | template-transform | Code нода |
|--------|--------------------|-----------|
| Форматировать текст из переменных | ✅ проще | можно, но избыточно |
| Сложная логика / расчёты | ❌ | ✅ |
| HTTP запросы | ❌ | ✅ |
| Нужен не-string output | ❌ | ✅ |
| Собрать Markdown/HTML из массива | ✅ через for loop | можно |
| Conditional текст | ✅ через if/else | можно |

## Синтаксис переменных в Dify

Важно понимать разницу двух синтаксисов:

```
Jinja2 template (в template-transform):
  {{ variable }}                → работает
  {{ items[0] }}                → ✅ работает
  {% for i in items %}...{% endfor %}  → ✅ работает

Dify variable reference (в HTTP body, params, headers и т.д.):
  {{#node_id.variable_name#}}   → работает
  {{#node_id.items[0]#}}        → ❌ НЕ РАБОТАЕТ — нет поддержки indexing
```

Если нужен первый элемент массива в HTTP body — используй Code ноду для извлечения.
