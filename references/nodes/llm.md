> ⚠️ ИСТОЧНИК ИСТИНЫ: Pydantic-схема в бэкенде Dify (в пакете graphon.nodes (в entities.py для llm)).
> Если референс расходится с кодом — код прав. Перед генерацией DSL сверяй поля.

# LLM Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.
> Все примеры из реальных тестов.

## Что это

Нода для вызова больших языковых моделей (LLM). Поддерживает контекст, историю (память), зрение (vision), а также структурированный вывод (Structured Output).

## Базовая структура (DSL)

```json
{
  "id": "llm_node_id",
  "type": "custom",
  "data": {
    "title": "LLM",
    "type": "llm",
    "model": {
      "provider": "imdeniil/proxyapi-openrouter/proxyapi_openrouter",
      "name": "deepseek/deepseek-v4-flash",
      "mode": "chat",
      "completion_params": {
        "temperature": 0.5,
        "max_tokens": 512
      }
    },
    "prompt_template": [
      {
        "role": "user",
        "text": "Answer this query concisely: {{#start.query#}}"
      }
    ],
    "vision": {
      "enabled": false,
      "configs": { "variable_selector": [] }
    },
    "memory": {
      "enabled": false,
      "window": { "enabled": false, "size": 50 }
    },
    "context": {
      "enabled": false,
      "variable_selector": []
    },
    "structured_output_enabled": false,
    "reasoning_format": "separated"
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
- `text` (string) — сгенерированный ответ модели.
- `reasoning_content` (string) — цепочка рассуждений (thinking trace), если модель поддерживает рассуждения (например, DeepSeek-R1).
- `usage` (object) — статистика использования токенов и времени генерации.
- `structured_output` (object) — распарсенный JSON-объект, если включен Structured Output.

Доступ снаружи:
```json
["llm_node_id", "text"]
["llm_node_id", "reasoning_content"]
["llm_node_id", "structured_output"]
```

---

## Structured Output (Структурированный вывод)

Позволяет автоматически получать от модели валидный JSON, соответствующий JSON Schema.

### Включение в DSL:

```json
{
  "structured_output_enabled": true,
  "structured_output": {
    "enabled": true,
    "schema": {
      "type": "object",
      "properties": {
        "answer": { "type": "number", "description": "The result of calculation" }
      },
      "required": ["answer"]
    }
  }
}
```

### Верифицировано на практике (T-08) ✅:
- Провайдер: `imdeniil/proxyapi-openrouter/proxyapi_openrouter`
- Модель: `deepseek/deepseek-v4-flash`
- **Результат**: Работает без ошибок. Под капотом Dify передаёт нужные параметры (`response_format: {"type": "json_object"}` или нативный json schema) и возвращает распарсенное значение.
- Утверждение о том, что `structured_output_enabled` ломает вызовы через ProxyAPI/OpenRouter, **НЕ подтвердилось** для актуальных моделей.

### Результат выполнения в workflow:
```json
"outputs": {
  "text": "{\"answer\": 4}",
  "structured_output": {
    "answer": 4
  }
}
```

---

## Настройка памяти (Memory Config)

⚠️ **Критическая особенность валидации Pydantic**:
Если в DSL передаётся объект `"memory"`, то поле `"window"` является **обязательным**, даже если память выключена.

```json
// ❌ Вызовет ValidationError в Dify worker:
"memory": { "enabled": false }

// ✅ Правильный формат:
"memory": {
  "enabled": false,
  "window": { "enabled": false, "size": 50 }
}
```

---

## Обработка рассуждений (Reasoning Format)

Для моделей класса reasoning (например, DeepSeek R1) Dify предоставляет настройку `reasoning_format`:

| Режим | Описание | Результат |
|-------|----------|-----------|
| `separated` | Рассуждения очищаются из `text` и возвращаются отдельно | `text` = чистый ответ, `reasoning_content` = мысли |
| `tagged` | Текст содержит оригинальные теги `<think>` | `text` = `<think>мысли</think> ответ` |

Для автоматизации в workflow строго рекомендуется использовать `"reasoning_format": "separated"`, чтобы не заниматься парсингом тегов вручную в Code-нодах.
