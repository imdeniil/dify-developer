> ⚠️ ИСТОЧНИК ИСТИНЫ: Pydantic-схема в бэкенде Dify (в ~/dify/api/core/workflow/nodes/knowledge_retrieval/entities.py).
> Если референс расходится с кодом — код прав. Перед генерацией DSL сверяй поля.

# Knowledge Retrieval Node — Верифицированный справочник

> Протестировано на Dify 1.14.2 self-hosted, 2026-06-18.

## Что это

Нода извлечения знаний (`knowledge-retrieval`) выполняет семантический поиск по базам знаний Dify (Datasets). Она принимает текстовый запрос на естественном языке, сопоставляет его с векторным или текстовым индексом базы знаний и возвращает список наиболее релевантных текстовых фрагментов (чанков).

## Базовая структура (DSL)

```json
{
  "id": "retrieval_node_id",
  "type": "custom",
  "data": {
    "title": "Retrieval",
    "type": "knowledge-retrieval",
    "query_variable_selector": ["start", "query"],
    "dataset_ids": ["90a5a988-48e5-4a6b-9e9d-1dcaae2ac179"],
    "retrieval_mode": "multiple",
    "multiple_retrieval_config": {
      "top_k": 3,
      "score_threshold_enabled": false,
      "score_threshold": 0.5,
      "reranking_enable": true,
      "reranking_model": {
        "provider": "cohere",
        "model": "rerank-multilingual-v3.0"
      }
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

## Параметры ноды

- `query_variable_selector` (array) — путь к переменной, содержащей текст поискового запроса.
- `dataset_ids` (array) — список UUID баз знаний, по которым осуществляется поиск.
- `retrieval_mode` (string) — режим поиска:
  - `"single"` — используется одна база знаний, параметры поиска наследуются из ее глобальных настроек.
  - `"multiple"` — продвинутый режим, параметры поиска задаются прямо в ноде графа.
- `multiple_retrieval_config` (object) — параметры поиска для режима `multiple`:
  - `top_k` (int) — лимит количества возвращаемых фрагментов (Top-K).
  - `score_threshold_enabled` (bool) — включение фильтрации по схожести.
  - `score_threshold` (float) — минимальный порог схожести (Similarity Score) от 0.0 до 1.0.
  - `reranking_enable` (bool) — включение модели Rerank для постобработки и переупорядочивания результатов.
  - `reranking_model` (object) — конфигурация модели Rerank. **Важно:** на уровне workflow/DSL ключи должны называться именно `provider` и `model` (они мапятся на Pydantic-поля бэкенда `reranking_provider_name` и `reranking_model_name` через validation aliases):
    - `provider` (string) — идентификатор провайдера (например, `"cohere"`).
    - `model` (string) — имя модели (например, `"rerank-multilingual-v3.0"`).

## Outputs

Нода `knowledge-retrieval` возвращает:
- `result` (array) — массив найденных фрагментов текста.

Каждый элемент в массиве `result` имеет следующую структуру:
```json
{
  "content": "Текст найденного фрагмента...",
  "title": "Название исходного документа.pdf",
  "doc_id": "document-uuid",
  "dataset_id": "dataset-uuid",
  "score": 0.85
}
```

Доступ снаружи:
```json
["retrieval_node_id", "result"]
```

---

## ⚠️ Особенности верификации (T-21) ✅

1. **Поведение при пустых результатах**:
   Если по запросу в базах знаний ничего не найдено (или база знаний пуста/только что создана), нода завершается успешно (`status: succeeded`) и возвращает пустой список:
   ```json
   "outputs": {
     "result": []
   }
   ```
   В последующих LLM-нодах рекомендуется делать проверку на пустоту RAG-контекста или передавать его через шаблонизатор, который корректно обработает пустой список.

2. **Векторный поиск (High-Quality) vs Поиск по ключевым словам (Economy)**:
   - При использовании баз знаний типа **High-Quality** (с эмбеддингами) поддерживаются все методы извлечения: векторный, полнотекстовый и гибридный.
   - Для баз знаний типа **Economy** (индекс строится по 10 ключевым словам без эмбеддингов) семантический векторный поиск недоступен, выполняется полнотекстовый поиск по ключевым словам. Нода в workflow абстрагирует эту разницу и работает прозрачно для пользователя.
