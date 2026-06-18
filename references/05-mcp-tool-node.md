# MCP Tool Node — специфика и грабли

## Создание MCP provider

```bash
POST /console/api/workspaces/current/tool-provider/mcp
{
  "server_url": "https://example.com/sse",
  "name": "My MCP",
  "icon": "🔌",
  "icon_type": "emoji",
  "icon_background": "#000000",
  "server_identifier": "my-mcp",      # уникальный ID
  "configuration": {},
  "headers": {
    "Authorization": "Bearer xxxxxxx"
  },
  "authentication": {}
}
```

Response: `{id, name, tools: [...], ...}`

⚠️ **`id`** (UUID) и **`server_identifier`** (твой chosen slug) — **разные вещи**. Сохраняй оба.

## Создание tool node в graph

```yaml
- data:
    title: MCP Tool
    type: tool
    provider_id: 'my-mcp'              # ← server_identifier, НЕ UUID!
    provider_type: mcp
    provider_name: 'My MCP'
    tool_name: 'some_tool'             # точное имя tool из MCP
    tool_label: 'some_tool'
    tool_parameters:
      param1:
        type: variable                 # array/string/int → variable для safety
        value: ['<source_node>', 'param1_value']
      static_param:
        type: constant
        value: 'fixed'
    tool_configurations: {}
    plugin_id: ''
  height: 89
  id: '<unique_node_id>'
  position: { x, y }
  ...
```

## ⚠️ Грабли

### 1. provider_id должен быть server_identifier, не UUID

**НЕправильно:**
```yaml
provider_id: '9f3ac3d6-1c00-4843-a75d-1fd4725c8dd0'   # UUID
```
→ `ToolProviderNotFoundError: mcp provider <uuid> not found`

**Правильно:**
```yaml
provider_id: 'telegram-mcp'   # server_identifier
```

См. `~/dify/api/services/tools/mcp_tools_manage_service.py:103-114` — `get_provider(server_identifier=...)` ищет по server_identifier.

### 2. Array параметры через type: constant ломаются

**НЕправильно для array параметров MCP:**
```yaml
tool_parameters:
  entities:
    type: constant
    value: ["-1001292405242", "-1001234567890"]
```
→ MCP получает значение в неправильном формате (массив конвертируется в string или ломается). Возврат: 0 results без ошибок.

**Правильно для array:**
```yaml
# 1. Создать Code node который возвращает array
- data:
    type: code
    code: |
      def main() -> dict:
          return {"entities": ["-1001292405242"]}   # array of strings
    outputs:
      entities: { type: 'array[string]', children: null }

# 2. В tool node ссылаться на эту Code node
tool_parameters:
  entities:
    type: variable
    value: ['<code_node_id>', 'entities']
```

### 3. tool_parameters entities type enum

В graphon валидаторе type может быть только:
- `'variable'`
- `'constant'`
- `'mixed'`

**НЕ:**
- `'array'` (не входит в enum)
- `'string'`
- и т.д.

Для array значений — type='variable' (через Code) или type='mixed' (template).

### 4. tool_parameters после выполнения

Dify экспонирует outputs MCP как **отдельные переменные** в outputs:

```python
# MCP tool возвращает {results, chats_processed, truncated}
# Dify автоматически "распаковывает" в:
outputs = {
    'text': '',                          # text output MCP tool
    'files': [],                         # files output
    'json': [...],                       # original JSON output
    'results': [...],                    # auto-extracted top-level key
    'chats_processed': 0,                # auto-extracted top-level key
    'truncated': False                   # auto-extracted top-level key
}
```

В следующем node: `value_selector: ['<mcp_node_id>', 'results']` для доступа к массиву.

### 5. MCP provider setup внутри tool_parameters

Для MCP tools где credentials нужны **per-call** (например, Bearer header), передаются при создании provider через `headers`:

```bash
POST /workspaces/current/tool-provider/mcp
{
  "server_url": "...",
  "headers": {"Authorization": "Bearer xxx"},
  ...
}
```

Headers шифруются в БД. В tool node их указывать **не нужно**.

## Стандартные MCP tools (mcp-telegram как пример)

MCP server экспонирует tools через JSON-RPC. Dify их автоматически листает.

```
get_folders          # без параметров
get_folder_chats     # {folder_id: int}
get_messages         # {entity: str, limit: int, ...}
export_messages      # {entities: array, start_date, end_date, per_chat_limit, max_chats}
send_message         # {entity, message, ...}
search_dialogs       # {query}
```

Подключение MCP:

1. Создать provider через Console API
2. Получить server_identifier
3. В DSL graph — tool node с provider_id=server_identifier
4. tool_parameters по схеме tool

## Debug

### MCP tool возвращает пустой результат

1. Проверить что **provider_id = server_identifier**, не UUID
2. Для array параметров — попробовать `type: variable` через Code
3. Сверить параметры с MCP serverом напрямую (через Python mcp client):

```python
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def test():
    async with sse_client(URL, headers=HEADERS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            r = await session.call_tool('tool_name', {params})
            for c in r.content:
                if hasattr(c, 'text'):
                    print(c.text)

asyncio.run(test())
```

Запуск: `uv run --with "mcp>=1.6" python test.py`

### Schema MCP tool

```python
tools = await session.list_tools()
for t in tools.tools:
    if t.name == 'target_tool':
        print(t.inputSchema)  # JSON Schema
```

## Network considerations для self-hosted

- Dify ходит к MCP через **SSRF proxy** (Squid) — нужно убедиться что Squid не блокирует target URL
- Для private/loopback ranges — добавить ACL в `~/dify/docker/volumes/ssrf_proxy/squid.conf`
- Для public HTTPS — должно работать из коробки
