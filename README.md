# Dify Developer

**Dify Developer** — это готовый набор инструментов (CLI-утилита, шаблоны и база знаний) для автоматизации разработки, тестирования, отладки и деплоя Dify-приложений (workflows/chatflows) v1.14.2 через Dify Console API.

Проект создан для того, чтобы избавить разработчиков от рутинного ручного кликания в UI Dify и позволить управлять жизненным циклом сценариев прямо из терминала или через ИИ-ассистентов.

---

## Основные возможности

1. **Dify Workflow CLI (`dify_dev_cli.py`)**:
   - Автоматический импорт сценариев из YAML DSL.
   - Запуск и интерактивное тестирование draft-версий сценариев с чтением логов (SSE-потока) в реальном времени.
   - Прохождение шагов с подтверждением человеком (**Human-in-the-Loop**) прямо из CLI.
   - Управление жизненным циклом (публикация, удаление приложений).
2. **База знаний и спецификации (Reference)**:
   - Подробные спецификации схем данных для всех типов нод Dify (в каталоге `references/nodes/`).
   - Руководства по сложным темам: обработка выводов LLM, интеграция MCP-серверов, отслеживание состояний между запусками и организация связей/переходов между узлами графа.
3. **Готовые шаблоны сценариев (Examples)**:
   - Практические кейсы (например, периодический сборщик дайджеста вакансий с дедупликацией).
   - Шаблоны конфигураций для разных типов нод.

---

## Быстрый старт

### 1. Установка и настройка
Склонируйте репозиторий в удобное место:
```bash
git clone https://github.com/imdeniil/dify-developer.git
cd dify-developer
```

Создайте файл `.env` в корневом каталоге вашего основного проекта (или скопируйте значения) со следующими переменными:
```ini
DIFY_BASE_URL=http://localhost:3006
DIFY_CONSOLE_TOKEN=dify-admin-ваш-токен
DIFY_WORKSPACE_ID=ваш-workspace-id
```
*Подробнее про авторизацию см. в [references/09-auth-and-access.md](references/09-auth-and-access.md).*

### 2. Автоматическая инициализация (Bootstrap)
Запустите команду начальной настройки:
```bash
python3 scripts/dify_dev_cli.py setup
```
**Что сделает эта команда:**
1. Склонирует официальную документацию Dify в `~/dify-docs/` (с `depth=1` для экономии места).
2. Настроит субагент для Claude Code в `~/.claude/agents/dify-docs.md`, чтобы ИИ мог быстро искать информацию по докам.

---

## Использование CLI

Все взаимодействия с Dify Console API осуществляются через скрипт `scripts/dify_dev_cli.py`. Авторизация (`DIFY_CONSOLE_TOKEN`, `DIFY_WORKSPACE_ID`, `DIFY_BASE_URL`) автоматически подгружается из файла `.env` в корне проекта.

### 1. Управление приложениями (Workflows/Chatflows)

* **Импорт приложения из DSL (YAML)**:
  ```bash
  python3 scripts/dify_dev_cli.py import --file <path_to_yaml> [--name <name>] [--app-id <app_id>] [--description <desc>] [--icon <emoji>] [--icon-background <bg>]
  ```
  Импортирует новый workflow или обновляет существующий (если передан `--app-id`).
* **Экспорт YAML DSL приложения**:
  ```bash
  python3 scripts/dify_dev_cli.py export --app-id <app_id> [--output <path_to_file>]
  ```
  Сохраняет текущую опубликованную конфигурацию в файл YAML DSL.
* **Список приложений в workspace**:
  ```bash
  python3 scripts/dify_dev_cli.py list-apps [--page <page>] [--limit <limit>] [--name <name>] [--mode <mode>]
  ```
  Выводит таблицу со всеми приложениями (ID, имя, режим, статус публикации, иконка, дата обновления).
* **Показать подробные метаданные приложения**:
  ```bash
  python3 scripts/dify_dev_cli.py show-app --app-id <app_id>
  ```
  Выводит детальную информацию о конкретном workflow в формате JSON.
* **Публикация (Deploy)**:
  ```bash
  python3 scripts/dify_dev_cli.py publish --app-id <app_id>
  ```
  Опубликовать текущую draft-версию workflow.
* **Удаление приложения**:
  ```bash
  python3 scripts/dify_dev_cli.py delete --app-id <app_id>
  ```
  Полностью удаляет приложение из Dify.

### 2. Тестирование и отладка (Runtimes & Runs)

* **Интерактивный запуск черновика (Draft Run)**:
  ```bash
  python3 scripts/dify_dev_cli.py test --app-id <app_id> [--inputs '<json_string>'] [--files '<json_string>']
  ```
  Запуск draft-версии с чтением SSE-потока событий. Поддерживает передачу файлов для мультимодальных моделей (передаются в `--files` в формате JSON-массива объектов с полями `type`, `transfer_method`, `url`/`upload_file_id`).
* **Прохождение Human-in-the-Loop (HITL)**:
  Приостановленное выполнение на ноде `Human Input` выведет `form_token`. Отправьте ответ формы:
  ```bash
  python3 scripts/dify_dev_cli.py submit-form --token <form_token> --action <action_id> [--inputs '<json_string>']
  ```
* **Получение лога событий**:
  ```bash
  python3 scripts/dify_dev_cli.py get-events --run-id <run_id>
  ```
  Позволяет дочитать поток событий после продолжения HITL или других прерываний.
* **Список истории запусков**:
  ```bash
  python3 scripts/dify_dev_cli.py list-runs --app-id <app_id> [--limit <limit>] [--page <page>] [--status <status>]
  ```
  Отображает список всех запусков workflow и их статусы.
* **Принудительная остановка выполнения**:
  ```bash
  python3 scripts/dify_dev_cli.py stop-run --app-id <app_id> --run-id <run_id>
  ```
  Останавливает выполняющийся запуск workflow.
* **Проверка зависимостей приложения**:
  ```bash
  python3 scripts/dify_dev_cli.py check-deps --app-id <app_id>
  ```
  Проверяет используемые в графе модели, плагины и MCP-серверы на доступность в вашем workspace.
* **Экспорт/импорт сырого JSON-графа (Draft JSON)**:
  ```bash
  # Получить текущий JSON графа
  python3 scripts/dify_dev_cli.py get-draft-json --app-id <app_id> [--output <path_to_file>]
  
  # Импортировать JSON графа напрямую
  python3 scripts/dify_dev_cli.py update-draft-json --app-id <app_id> --file <path_to_json_file>
  ```

### 3. Управление API-ключами приложения

* **Список ключей**:
  ```bash
  python3 scripts/dify_dev_cli.py list-keys --app-id <app_id>
  ```
* **Создание нового ключа**:
  ```bash
  python3 scripts/dify_dev_cli.py create-key --app-id <app_id>
  ```
* **Удаление ключа**:
  ```bash
  python3 scripts/dify_dev_cli.py delete-key --app-id <app_id> --key-id <key_id>
  ```

### 4. Управление MCP-серверами (Workspace Level)

* **Список MCP-серверов**:
  ```bash
  python3 scripts/dify_dev_cli.py list-mcp
  ```
* **Добавление нового MCP-сервера**:
  ```bash
  python3 scripts/dify_dev_cli.py add-mcp --name <name> --url <url> --identifier <id> [--icon <emoji>] [--headers <json_or_pairs>] [--timeout <timeout>] [--sse-timeout <sse_timeout>]
  ```
* **Обновление параметров MCP-сервера**:
  ```bash
  python3 scripts/dify_dev_cli.py update-mcp --provider-id <id_name_or_uuid> [--name <name>] [--url <url>] [--identifier <id>] [--icon <emoji>] [--headers <json_or_pairs>] [--timeout <timeout>] [--sse-timeout <sse_timeout>]
  ```
* **Удаление MCP-сервера**:
  ```bash
  python3 scripts/dify_dev_cli.py delete-mcp --provider-id <id_name_or_uuid>
  ```
  MCP-сервер можно удалять или обновлять, указывая его UUID, название (`name`) или идентификатор (`identifier`).

### 5. Настройка моделей и провайдеров (Workspace Admin Level)

* **Список активных провайдеров и моделей**:
  ```bash
  python3 scripts/dify_dev_cli.py list-models
  ```
* **Модели по умолчанию для workspace**:
  ```bash
  # Получить модель по умолчанию для типа (например, llm, text-embedding)
  python3 scripts/dify_dev_cli.py get-default-model --model-type <type>
  
  # Установить модель по умолчанию
  python3 scripts/dify_dev_cli.py set-default-model --model-type <type> --model <model> --provider <provider>
  ```
* **Настройка ключей доступа к провайдерам ИИ (API Credentials)**:
  ```bash
  # Посмотреть текущую конфигурацию провайдера
  python3 scripts/dify_dev_cli.py get-model-credentials --provider <provider>
  
  # Сохранить/создать API-ключи провайдера
  python3 scripts/dify_dev_cli.py set-model-credentials --provider <provider> --credentials <json_string> [--name <name>]
  
  # Проверить подключение с указанными ключами
  python3 scripts/dify_dev_cli.py validate-model-credentials --provider <provider> --credentials <json_string>
  ```

### 6. Работа с опубликованными приложениями (Service API)

Для работы с этой группой команд вам понадобится API-ключ конкретного опубликованного приложения (`app-xxxxxxxx`). Его можно сгенерировать в UI Dify или получить программно через команду `create-key`. Ключ можно передавать через аргумент `--app-key` или задать в `.env` как переменную `DIFY_APP_KEY`. Если указан аргумент `--app-id`, CLI автоматически получит или создаст API-ключ для этого приложения.

* **Запуск опубликованного workflow (App Run)**:
  ```bash
  python3 scripts/dify_dev_cli.py app-run [--app-key <key>] [--app-id <app_id>] [--inputs '<json_string>'] [--files '<json_string>'] [--no-streaming] [--user <user>]
  ```
  По умолчанию запускает выполнение в интерактивном режиме SSE-стриминга логов.
* **Принудительная остановка таска (App Stop)**:
  ```bash
  python3 scripts/dify_dev_cli.py app-stop [--app-key <key>] --task-id <id> [--user <user>]
  ```
* **Получить детальный статус и результат запуска (App Run Detail)**:
  ```bash
  python3 scripts/dify_dev_cli.py app-run-detail [--app-key <key>] --run-id <run_id>
  ```
* **Получить входные параметры приложения (App Parameters)**:
  ```bash
  python3 scripts/dify_dev_cli.py app-parameters [--app-key <key>]
  ```
  Возвращает схему ожидаемых переменных и настройки лимитов загрузки файлов.
* **Загрузка файла на сервер Dify (App File Upload)**:
  ```bash
  python3 scripts/dify_dev_cli.py app-upload [--app-key <key>] --file <path_to_local_file> [--user <user>]
  ```
  Возвращает JSON с `id` загруженного файла, который затем можно передать в качестве значения для файловой переменной на шаге `app-run`.
* **Запуск и тестирование Chatflow (test-chatflow)**:
  ```bash
  python3 scripts/dify_dev_cli.py test-chatflow [--app-key <key>] [--app-id <app_id>] --query <query> [--inputs '<json_string>'] [--files '<json_string>'] [--conversation-id <id>] [--no-streaming] [--user <user>]
  ```
  Использует Service API `/v1/chat-messages` для взаимодействия с Chatflow-приложениями. Поддерживает SSE-стриминг ответа ассистента.

### 7. Управление Базами Знаний (Datasets / Knowledge Base)

Позволяет полностью автоматизировать управление коллекциями документов и проверку качества RAG.

* **Список баз знаний**:
  ```bash
  python3 scripts/dify_dev_cli.py list-datasets [--page <page>] [--limit <limit>]
  ```
* **Создание базы знаний**:
  ```bash
  python3 scripts/dify_dev_cli.py create-dataset --name <name> [--description <desc>] [--indexing-technique high_quality|economy] [--permission only_me|all_team_members|partial_members]
  ```
* **Обновление настроек (Patch)**:
  ```bash
  python3 scripts/dify_dev_cli.py patch-dataset --dataset-id <id> [--name <name>] [--description <desc>] [--permission <permission>] [--indexing-technique <technique>] [--embedding <provider/model>] [--threshold <float>]
  ```
* **Список документов базы знаний**:
  ```bash
  python3 scripts/dify_dev_cli.py list-documents --dataset-id <dataset_id> [--page <page>] [--limit <limit>]
  ```
* **Загрузка и индексация локального документа**:
  ```bash
  python3 scripts/dify_dev_cli.py upload-document --dataset-id <dataset_id> --file <path_to_file> [--doc-form text_model|qa_model] [--separator <sep>] [--max-tokens <int>] [--chunk-overlap <int>]
  ```
  Автоматически загружает файл во временное хранилище Dify Console, после чего запускает индексацию с правилами разметки (автоматический режим или кастомное разбиение по токенам/разделителям).
* **Удаление документа**:
  ```bash
  python3 scripts/dify_dev_cli.py delete-document --dataset-id <dataset_id> --document-id <document_id>
  ```
* **Тестирование извлечения / Hit Testing**:
  ```bash
  python3 scripts/dify_dev_cli.py retrieve --dataset-id <dataset_id> --query <query_text> [--top-k <int>] [--threshold <float>]
  ```
  Выполняет тестовый запрос поиска по базе знаний с выводом скора релевантности и отрывков найденных сегментов.

### 8. Запуск тестов
Для проверки работоспособности клиента выполните:
```bash
python3 -m unittest scripts/test_cli.py
```

---

## Структура репозитория

```
dify-developer/
├── README.md                 # Описание проекта
├── SKILL.md                  # Системные инструкции для подключения как ИИ-скилла
├── scripts/
│   └── dify_dev_cli.py       # CLI-утилита для работы с API Dify
├── examples/                 # Практические примеры и шаблоны
│   ├── jobs-digest-case-...  # Разбор сложного кейса (дайджест вакансий)
│   ├── external-state-pat... # Шаблон организации state между запусками
│   ├── healthcheck-pattern.md# Шаблон проверки работоспособности
│   └── *.json, *.yml         # Минимальные DSL-шаблоны нод
└── references/               # База знаний по разработке
    ├── nodes/                # Спецификации всех 21 нод (llm, code, loop и т.д.)
    ├── 01-console-api-e...   # Справочник API Dify
    ├── 05-mcp-tool-node.md   # Нюансы работы с MCP-серверами
    ├── 08-gotchas-and-l...   # Важные баги Dify и обходы (12 пунктов)
    ├── 10-llm-output-pi...   # Решение проблем с парсингом и качеством ответов LLM
    └── 15-transitions-a...   # Правила связей (Edges) и ветвления в графе
```

---

## Подключение в качестве ИИ-скилла (Claude Code / Gemini Kit)

Этот репозиторий спроектирован так, чтобы его можно было использовать в качестве **Skill** для агентов ИИ. 

Для интеграции с **Claude Code** скрипт `setup` автоматически создает агента, к которому можно обращаться для быстрого поиска по документации:
`dify-docs` — осуществляет семантический и текстовый поиск по официальным докам Dify в `~/dify-docs/en/`.

Инструкции для ИИ-разработчика по генерации DSL и работе с этим репозиторием описаны в файле [SKILL.md](SKILL.md).

---

## Системные требования

- Dify v1.14.2 (self-hosted)
- Python 3.10+
- Доступ к сети с инстанса Dify до вызываемых API/MCP.
