# Dify Workflow Dev — Reference для будущих skills

База знаний для разработки Dify workflows через Console API. Собрана из реальной практики (создание `jobs-digest` проекта, 2026-06-17, Dify 1.14.2).

## Цель

Когда нужно создать/изменить/отладить Dify workflow — использовать этот reference вместо ресёрча каждый раз. Особенно полезно для построения **skills** в Claude Code и Gemini Kit, которые автоматизируют рутину workflow разработки.

## Структура

| Файл | Что внутри |
|---|---|
| [01-console-api-endpoints.md](references/01-console-api-endpoints.md) | Все endpoints для работы с workflow через API |
| [02-dsl-format.md](references/02-dsl-format.md) | YAML DSL формат для импорта apps |
| [03-node-types.md](references/03-node-types.md) | Справочник всех node types + их data schemas |
| [04-variable-templating.md](references/04-variable-templating.md) | Variables: variable/constant/mixed, environment vars, templating |
| [05-mcp-tool-node.md](references/05-mcp-tool-node.md) | Специфика MCP tool node (частые грабли) |
| [06-llm-node-gotchas.md](references/06-llm-node-gotchas.md) | LLM node: Anthropic/GLM нюансы, structured output |
| [07-run-and-debug.md](references/07-run-and-debug.md) | Как запускать, парсить SSE, дебажить |
| [08-gotchas-and-lessons.md](references/08-gotchas-and-lessons.md) | Баги, обходы, lessons learned (12 пунктов) |
| [09-auth-and-access.md](references/09-auth-and-access.md) | ADMIN_API_KEY, X-WORKSPACE-ID заголовок |
| [10-llm-output-pitfalls.md](references/10-llm-output-pitfalls.md) | LLM output pitfalls — галлюцинации, обрезы, parsing (12 пунктов + patterns) |
| [examples/](examples/) | Готовые шаблоны: minimal, MCP tool, LLM, HTTP, **jobs-digest case study**, **healthcheck pattern** |
| [nodes/](references/nodes/) | Верифицированные спецификации нод: [code](references/nodes/code.md), [http-request](references/nodes/http-request.md), [if-else](references/nodes/if-else.md), [iteration](references/nodes/iteration.md), [llm](references/nodes/llm.md), [template-transform](references/nodes/template-transform.md), [variable-aggregator](references/nodes/variable-aggregator.md), [question-classifier](references/nodes/question-classifier.md), [parameter-extractor](references/nodes/parameter-extractor.md), [list-operator](references/nodes/list-operator.md), [document-extractor](references/nodes/document-extractor.md), [loop](references/nodes/loop.md), [human-input](references/nodes/human-input.md), [start](references/nodes/start.md), [end](references/nodes/end.md), [answer](references/nodes/answer.md), [variable-assigner](references/nodes/variable-assigner.md), [knowledge-retrieval](references/nodes/knowledge-retrieval.md), [tool](references/nodes/tool.md), [agent](references/nodes/agent.md), [trigger](references/nodes/trigger.md) |
| [11-annotations.md](references/11-annotations.md) | Annotations (Annotation Reply): CRUD Q&A пар, async enable job, batch import, embedding constraints |
| [12-monitoring-runs.md](references/12-monitoring-runs.md) | Мониторинг: workflow-runs, node-executions, counts, tracing (Langfuse), conversation variables |
| [13-app-management.md](references/13-app-management.md) | App lifecycle: создание/копирование/экспорт/публикация, API keys, site/API enable |
| [14-platform-coverage.md](references/14-platform-coverage.md) | **Сводная таблица** покрытия: все 21 нод + platform entities, статус верификации, constraints |
| [15-transitions-and-edges.md](references/15-transitions-and-edges.md) | **Связи и переходы** (Edges & Routing): типы, структура в DSL, область видимости переменных |
| [16-unverified-features.md](references/16-unverified-features.md) | **Неверифицированные возможности**: список настроек и комбинаций, не проходивших живые тесты |


## Использование в качестве Skill

Этот каталог зарегистрирован как Skill `dify-developer` в системе Gemini Kit и Claude Code. 

При активации скилл выполняет автоматический разбор бизнес-требований, генерацию YAML DSL, импорт через Console API, интерактивный тест-ран с обработкой пауз Human-in-the-Loop и публикацию.

### Автоматическая инициализация (Bootstrap) и CLI

Скилл полностью автономен. При первом запуске он автоматически инициализирует окружение с помощью скрипта:
```bash
python3 scripts/dify_dev_cli.py setup
```
Эта команда сама склонирует репозиторий официальной документации Dify в `~/dify-docs/` (через depth=1 для скорости) и создаст конфигурацию субагента для Claude Code.

Также CLI-скрипт используется ИИ-ассистентом для выполнения API-вызовов в Dify (импорт, запуск, прохождение HITL-форм, публикация). Подробнее см. в [SKILL.md](SKILL.md).

### Приоритет чтения для ИИ при разработке:

1. **references/08-gotchas-and-lessons.md** — известные баги (избежать повторения)
2. **references/10-llm-output-pitfalls.md** — паттерны парсинга ответов LLM
3. **references/05-mcp-tool-node.md** — если workflow использует MCP
4. **references/06-llm-node-gotchas.md** — если есть LLM nodes
5. **examples/jobs-digest-case-study.md** — подробный пример разработки
6. **references/01-console-api-endpoints.md** — API reference
7. **references/03-node-types.md** — схемы для конкретного типа нод
8. **examples/** — шаблоны для копирования

## Версии

- Dify: 1.14.2 (self-hosted)
- Plugin daemon: 0.6.1
- Python: 3.12.3 (в plugin_daemon контейнере)
- Источник: реальная практика + `~/dify/api/` source code

## Связанные ресурсы

- **Running Dify**: http://localhost:3006
- **Source code**: `~/dify/api/` (backend), `~/dify/web/` (frontend)
- **Документация**: `~/dify-docs/en/`
- **Workspace**: `~/defyproj/`
- **CLAUDE.md**: `~/defyproj/CLAUDE.md` — общий контекст
- **GEMINI.md**: `~/defyproj/GEMINI.md` — специфика Dify-сервисов
