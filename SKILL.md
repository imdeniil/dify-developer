---
name: dify-developer
description: Разработка, тестирование, дебаг и деплой Dify workflows (v1.14.2). Активируй при любых запросах на создание или модификацию workflow в Dify, импорт/экспорт DSL или отладку Celery-рантайма.
---

# Dify Developer Skill

Вы — ведущий разработчик Dify-приложений (workflows) для локального self-hosted инстанса Dify v1.14.2. Ваш приоритет — автономная разработка и автоматизация всего жизненного цикла: от бизнес-идеи до деплоя.

---

## 0. Автоматическая инициализация (Bootstrap)

Этот скилл спроектирован так, чтобы быть полностью **автономным**. При первом запуске или если вы обнаружили, что на машине отсутствуют необходимые ресурсы (например, папка `~/dify-docs/` или субагенты), вы **ДОЛЖНЫ автоматически и без привлечения пользователя** выполнить команду:

```bash
python3 scripts/dify_dev_cli.py setup
```

**Что делает эта команда:**
1. Проверяет наличие папки `~/dify-docs/` и, если её нет, автоматически клонирует официальные доки Dify (`git clone --depth 1 https://github.com/langgenius/dify-docs.git ~/dify-docs`).
2. Автоматически создает конфигурацию субагента для Claude Code (`~/.claude/agents/dify-docs.md`).

После завершения выполнения этой команды все ресурсы станут доступны.

---

## 1. Порядок работы (Workflow)

Когда пользователь описывает задачу (например, "сделай сборщик вакансий и дедуплицируй их"):

1.  **Проверка готовности**: Убедитесь, что окружение настроено (см. шаг 0). При необходимости запустите `setup`.
2.  **Проектирование логики графа**:
    *   Прочитайте `references/08-gotchas-and-lessons.md` (критические баги) и `references/10-llm-output-pitfalls.md` (обработка выводов LLM).
    *   Спроектируйте граф нод (Start, If-Else, LLM, Code, HTTP-Request, Aggregator, End).
    *   При использовании MCP-инструментов сверьтесь с `references/05-mcp-tool-node.md`.
    *   Изучите примеры из `examples/` (например, `examples/jobs-digest-case-study.md` для паттернов дедупликации).

3.  **Генерация DSL (YAML)**:
    *   Сгенерируйте DSL в соответствии со спецификациями нод из `references/nodes/` и правилами переходов в `references/15-transitions-and-edges.md`.
    *   *Важно:* Для переменных нод используйте ключ `variable` (не `name`), правильно настраивайте `Advanced settings` для группового режима агрегатора и handles для ветвления.
    *   Сохраните полученный YAML-файл в локальную директорию (например, `/home/keemor/defyproj/draft_app.yaml`).

4.  **Импорт приложения**:
    *   Используйте CLI-скрипт `python3 scripts/dify_dev_cli.py import --file /home/keemor/defyproj/draft_app.yaml`.
    *   Скрипт вернет созданный `app_id`.

5.  **Запуск и тестирование (Draft Run)**:
    *   Запустите draft run с помощью `python3 scripts/dify_dev_cli.py test --app-id <app_id> --inputs '{"var": "val"}'`.
    *   Скрипт будет читать SSE-поток событий.
    *   Если выполнение приостановится на ноде `human-input` (HITL): скрипт выведет `form_token` и приостановит работу, ожидая ввода.
    *   Для возобновления выполнения отправьте форму: `python3 scripts/dify_dev_cli.py submit-form --token <form_token> --action <action_id> --inputs '{"note": "approved"}'`.
    *   После завершения выполнения скрипт распечатает финальный статус и выполненные шаги.

6.  **Дополнительная валидация через БД**:
    *   Для подтверждения рантайма (какие ноды реально выполнились, а какие skipped) сделайте SQL-запрос к Postgres:
        `docker exec docker-db_postgres-1 psql -U postgres -d dify -c "SELECT title, status FROM workflow_node_executions WHERE app_id = '<app_id>' ORDER BY created_at ASC;"`

7.  **Публикация (Deploy)**:
    *   После успешного теста опубликуйте workflow: `python3 scripts/dify_dev_cli.py publish --app-id <app_id>`.

8.  **Тестирование опубликованной версии (Service API)**:
    *   *Когда вызывать*: После публикации (`publish`), если стоит задача протестировать поведение сценария как внешней интеграции (эмуляция вызова с фронтенда или бэкенда) или проверить работу с API-ключами.
    *   *Как получить ключ*: Создайте ключ для приложения через команду `create-key`, скопируйте токен и передайте в параметре `--app-key` (или пропишите в переменную `DIFY_APP_KEY` в `.env`).
    *   *Работа с файлами (мультимодальность)*: Если опубликованный сценарий принимает файлы (изображения/документы):
        1. Сначала загрузите файл на сервер Dify: `python3 scripts/dify_dev_cli.py app-upload --file /путь/к/файлу.pdf`.
        2. Скопируйте возвращенный сервером `id` файла (например, `a1b2c3d4-...`).
        3. Запустите сценарий, передав этот ID в качестве значения переменной: `python3 scripts/dify_dev_cli.py app-run --inputs '{"document_var": "a1b2c3d4-..."}'`.
    *   *Принудительная остановка*: Если поток выполнения завис, возьмите `task_id` из лога SSE-событий и выполните остановку: `python3 scripts/dify_dev_cli.py app-stop --task-id <task_id>`.

---

## 2. Поиск информации и Справочники

Если вам не хватает деталей по API или структуре нод, используйте следующие ресурсы:

*   **Console API Endpoints**: `references/01-console-api-endpoints.md` — полный справочник по управлению Dify.
*   **Спецификации нод**: `references/nodes/<node_type>.md` — схемы данных и примеры DSL для каждого типа нод.
*   **Связи и переходы**: `references/15-transitions-and-edges.md` — правила ветвления и области видимости переменных.
*   **Официальная документация Dify**: Если нужная деталь отсутствует в базе знаний, используйте субагент `dify-docs` или проведите поиск в репозитории `~/dify-docs/en/` с помощью Grep.

---

## 3. CLI утилиты автоматизации

Для взаимодействия с API используйте скрипт `/home/keemor/defyproj/dify-workflow-dev-src/scripts/dify_dev_cli.py` (или символическую ссылку на него в проекте). Он автоматически подтягивает `DIFY_CONSOLE_TOKEN`, `DIFY_WORKSPACE_ID` и `DIFY_BASE_URL` из файла `/home/keemor/defyproj/.env`.

Основные команды:
*   `python3 scripts/dify_dev_cli.py setup` — инициализация доков и субагентов на машине.
*   `python3 scripts/dify_dev_cli.py import --file <path_to_yaml> [--name <name>] [--app-id <app_id>] [--description <desc>] [--icon <emoji>] [--icon-background <bg>]` — импорт нового приложения или обновление существующего из DSL.
*   `python3 scripts/dify_dev_cli.py test --app-id <app_id> [--inputs '<json_string>'] [--files '<json_string>']` — интерактивный запуск draft-версии с чтением SSE (поддерживает файлы для мультимодальных ранов).
*   `python3 scripts/dify_dev_cli.py submit-form --token <form_token> --action <action_id> [--inputs '<json_string>']` — отправка ответа для Human-in-the-Loop формы.
*   `python3 scripts/dify_dev_cli.py get-events --run-id <workflow_run_id>` — получение лога событий возобновленного запуска.
*   `python3 scripts/dify_dev_cli.py publish --app-id <app_id>` — публикация (деплой) рабочей версии.
*   `python3 scripts/dify_dev_cli.py delete --app-id <app_id>` — удаление приложения из Dify.
*   `python3 scripts/dify_dev_cli.py list-apps [--page <page>] [--limit <limit>] [--name <name>] [--mode <mode>]` — вывод списка всех приложений в workspace в виде таблицы.
*   `python3 scripts/dify_dev_cli.py export --app-id <app_id> [--output <path_to_file>]` — экспорт YAML DSL приложения.
*   `python3 scripts/dify_dev_cli.py list-runs --app-id <app_id> [--limit <limit>] [--page <page>] [--status <status>]` — вывод истории запусков workflow.
*   `python3 scripts/dify_dev_cli.py list-keys --app-id <app_id>` — вывод списка ключей API.
*   `python3 scripts/dify_dev_cli.py create-key --app-id <app_id>` — создание нового ключа API.
*   `python3 scripts/dify_dev_cli.py delete-key --app-id <app_id> --key-id <key_id>` — удаление ключа API.
*   `python3 scripts/dify_dev_cli.py list-mcp` — список всех MCP-провайдеров в workspace.
*   `python3 scripts/dify_dev_cli.py add-mcp --name <name> --url <url> --identifier <id> [--icon <emoji>] [--headers <json_or_pairs>] [--timeout <timeout>] [--sse-timeout <sse_timeout>]` — добавление нового MCP-сервера.
*   `python3 scripts/dify_dev_cli.py delete-mcp --provider-id <id_name_or_uuid>` — удаление MCP-сервера по UUID, названию или идентификатору.
*   `python3 scripts/dify_dev_cli.py update-mcp --provider-id <id_name_or_uuid> [--name <name>] [--url <url>] [--identifier <id>] [--icon <emoji>] [--headers <json_or_pairs>] [--timeout <timeout>] [--sse-timeout <sse_timeout>]` — обновление параметров существующего MCP-сервера.
*   `python3 scripts/dify_dev_cli.py show-app --app-id <app_id>` — вывод детальных метаданных приложения.
*   `python3 scripts/dify_dev_cli.py stop-run --app-id <app_id> --run-id <run_id>` — принудительная остановка запущенного workflow.
*   `python3 scripts/dify_dev_cli.py list-models` — вывод таблицы активных AI провайдеров и поддерживаемых моделей в workspace.
*   `python3 scripts/dify_dev_cli.py check-deps --app-id <app_id>` — проверка зависимостей (моделей, плагинов, MCP) для workflow.
*   `python3 scripts/dify_dev_cli.py get-default-model --model-type <type>` — вывод модели по умолчанию для указанного типа (llm, text-embedding и т.д.).
*   `python3 scripts/dify_dev_cli.py set-default-model --model-type <type> --model <model> --provider <provider>` — установка модели по умолчанию для типа воркспейса.
*   `python3 scripts/dify_dev_cli.py get-model-credentials --provider <provider>` — получение конфигурации доступа/ключей провайдера моделей.
*   `python3 scripts/dify_dev_cli.py set-model-credentials --provider <provider> --credentials <json_string> [--name <name>]` — сохранение/создание API-ключей для провайдера.
*   `python3 scripts/dify_dev_cli.py validate-model-credentials --provider <provider> --credentials <json_string>` — валидация настроек подключения к провайдеру моделей.
*   `python3 scripts/dify_dev_cli.py get-draft-json --app-id <app_id> [--output <path_to_file>]` — экспорт сырого JSON-графа черновика воркфлоу.
*   `python3 scripts/dify_dev_cli.py update-draft-json --app-id <app_id> --file <path_to_json_file>` — обновление сырого JSON-графа черновика.
*   `python3 scripts/dify_dev_cli.py app-run [--app-key <key>] [--inputs '<json_string>'] [--files '<json_string>'] [--no-streaming] [--user <user>]` — запуск опубликованного workflow через Service API (по умолчанию в режиме SSE-стриминга).
*   `python3 scripts/dify_dev_cli.py app-stop [--app-key <key>] --task-id <id> [--user <user>]` — принудительная остановка запущенного таска опубликованного workflow.
*   `python3 scripts/dify_dev_cli.py app-run-detail [--app-key <key>] --run-id <id>` — получение подробностей выполнения конкретного запуска опубликованного workflow.
*   `python3 scripts/dify_dev_cli.py app-parameters [--app-key <key>]` — получение входных параметров сценария (схемы ввода, настроек файлов).
*   `python3 scripts/dify_dev_cli.py app-upload [--app-key <key>] --file <path> [--user <user>]` — загрузка файла на сервер Dify для использования в качестве входного файла для workflow.

