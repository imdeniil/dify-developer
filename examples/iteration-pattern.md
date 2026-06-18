# Iteration Pattern — циклы в Dify workflow

Полный reference для Iteration node. Реальные примеры из jobs-digest Phase 2.

## Использование Iteration

Iteration нужен когда:
- Нужно обойти ограничение на вложенные массивы (array of arrays) или разбить большую нагрузку на батчи (chunks) для LLM
- Нужно вызвать MCP/HTTP/LLM для каждого элемента массива
- Multi-chunk отправка в Telegram (несколько messages)
- Batch processing

## Полная структура graph

```yaml
# 1. OUTER Iteration node (контейнер)
- data:
    title: Process Items
    type: iteration
    iterator_selector: [<source_node_id>, items_array]  # array to iterate
    iterator_input_type: array[string]                  # type of each element
    output_selector: [<inner_last_node_id>, result]     # what to collect per iter
    output_type: array[string]                          # type of collected
    is_parallel: false
    parallel_nums: 10
    error_handle_mode: terminated
    flatten_output: false
    start_node_id: <iteration_start_node_id>
  height: 178
  id: <iteration_node_id>
  parentId: null
  zIndex: 1

# 2. INNER Iteration start (обязательный)
- data:
    title: ''
    type: iteration-start
    isInIteration: true
  id: <iteration_start_node_id>
  parentId: <iteration_node_id>
  type: custom-iteration-start
  zIndex: 1002

# 3. INNER nodes (любые: code, llm, tool, http-request)
- data:
    title: Process Item
    type: code
    isInIteration: true
    isInLoop: false
    iteration_id: <iteration_node_id>
    variables:
      - variable: current_item
        value_selector: [<iteration_node_id>, item]  # ТЕКУЩИЙ ЭЛЕМЕНТ
        value_type: string
      # Можно ссылаться на outer nodes:
      - variable: outer_var
        value_selector: [<outer_node_id>, field]
  id: <inner_node_id>
  parentId: <iteration_node_id>
  zIndex: 1002
```

## Edges

```yaml
# INNER (внутри iteration) — между iter-start и inner nodes
- data:
    isInIteration: true
    isInLoop: false
    iteration_id: <iteration_node_id>
    sourceType: iteration-start
    targetType: code
  source: <iteration_start_node_id>
  sourceHandle: source
  target: <inner_node_id>
  targetHandle: target
  zIndex: 1002

# OUTER (вне iteration) — к iteration и из iteration
- data:
    isInIteration: false
    isInLoop: false
    sourceType: custom
    targetType: iteration
  source: <source_node_id>
  sourceHandle: source
  target: <iteration_node_id>
  targetHandle: target
  zIndex: 0
```

## Pattern: Chunking для больших массивов (обход ограничения array-of-arrays и батчинг)

```python
# BEFORE iteration — Code node разбивает массив на chunks
import json
def main(big_array: list) -> dict:
    chunks = [big_array[i:i+17] for i in range(0, len(big_array), 17)]
    # Каждый chunk как JSON string (обход ограничения на array-of-arrays в Dify)
    return {"chunks": [json.dumps(c) for c in chunks]}
    # output type: array[string]
```

```yaml
# Iteration обходит chunks
iterator_selector: [<chunker_node_id>, chunks]
iterator_input_type: array[string]
```

```python
# INSIDE iteration — Code node парсит JSON chunk обратно в array
def main(chunk_json: str) -> dict:
    items = json.loads(chunk_json) if isinstance(chunk_json, str) else chunk_json
    return {"items": items}
    # output type: array[string]
```

```python
# AFTER iteration — merge collected outputs
def main(iteration_output) -> dict:
    all_results = []
    items = iteration_output if isinstance(iteration_output, list) else [iteration_output]
    for item_json in items:
        try:
            data = json.loads(item_json) if isinstance(item_json, str) else item_json
            if isinstance(data, list):
                all_results.extend(data)
        except: pass
    return {"merged": json.dumps(all_results)}  # JSON string для следующего Code
```

## Pattern: Multi-message Telegram (несколько messages если summary длинная)

```python
# Code: разбить summary на chunks по 3500 char
def main(summary: str) -> dict:
    chunks = []
    current = ""
    for para in summary.split("\n\n"):
        if len(current) + len(para) + 2 > 3500:
            if current: chunks.append(current)
            current = para
        else:
            current = (current + "\n\n" + para) if current else para
    if current: chunks.append(current)
    return {"chunks": chunks, "count": len(chunks)}
```

```yaml
# Iteration по chunks → HTTP sendMessage каждый
iterator_selector: [<chunker_node_id>, chunks]
output_selector: [<http_inner_node_id>, status_code]
output_type: array[number]

# Внутри iteration — HTTP Request:
body:
  data: '{"chat_id": "{{#env.USER_ID#}}", "text": "{{#<iteration_node_id>.item#}}"}'
```

## Реальные примеры

### Jobs Digest Phase 2.1: Iteration для MCP (33 канала)

```
Date Calc (33 chat_ids → 2 chunks по 17)
  → [Iteration: Fetch Messages]
      iter-start
      Code: parse chunk JSON → entities array (17 items)
      MCP: export_messages(entities from Code, dates from Date Calc)
      Code: extract results → JSON string
  → Code: merge all chunks → combined results_json
  → Code: flatten → messages for LLM
```

App: `5af1637b-c5fc-4eb7-b985-7fd2cf7f1a4d` (v1.9)

### Jobs Digest Phase 2.2: Iteration для Telegram multi-chunk

```
LLM Summarizer → summary text
  → Code: chunk by 3500 char (chunks array)
  → [Iteration: Send Chunks]
      iter-start
      HTTP: sendMessage(text = iteration_item)
  → End
```

App: тот же (v1.8+)

## Known issues

1. **Если iteration inner node падает** — весь iteration fails (если error_handle_mode=terminated)
2. **`is_parallel: true`** — все итерации параллельно, но может overloaded LLM/API
3. **flatten_output: true** — если inner node возвращает array, iteration вернёт плоский array
4. **output_selector должен указывать на output field последнего inner node** — иначе данные потеряются

## Время выполнения

Iteration **последовательный** (is_parallel=false):
- 2 iterations × ~6 sec MCP = 12 sec
- 3 iterations × 30 sec LLM = 90 sec

Iteration **параллельный** (is_parallel=true):
- max(parallel_nums=10, actual_iterations) × single iter time
- ⚠️ Может перегрузить API (Z.ai overloaded_error)
