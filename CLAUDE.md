# Personal Assistant Bot

Telegram-бот — персональный ассистент владельца. Текст владельца уходит в `ai_framework`
(`ClaudeSdkProvider` — CLI Claude Code по подписке, `CLAUDE_CODE_OAUTH_TOKEN`), ответ модели возвращается в чат.
У модели нет Bash и доступа к файловой системе: встроенные инструменты CLI выключены, она действует только
через инструменты, объявленные в коде бота.

## Архитектура

```
Telegram <-> bot_framework <-> SendToAgentAction <-> ai_framework.AIApplication <-> CLI Claude Code (подписка)
                                                          |
                                                          +-- память диалога: Postgres, схема ai
```

### Структура проекта

```
workers/bot/
├── __main__.py              # Composition root: env, AIApplication, список tools, сборка хендлеров
├── transcriber_factory.py   # Выбор транскрайбера по VOICE_RECOGNITION_MODE
├── todoist_tools_factory.py # find_tasks, create_task поверх TodoistTaskService
└── gmail_tools_factory.py   # search_mail, read_mail, draft_reply поверх GmailClient (OAuth refresh token)
src/
├── ai_tools/                # Инструменты модели: пакет на инструмент, класс — наследник BaseTool
├── chat/
│   ├── actions/
│   │   ├── send_to_agent_action.py   # Текст → AIApplication.process_message → ответ в чат
│   │   ├── system_prompt_builder.py  # data/system_prompt.txt + сегодняшняя дата на каждый запрос
│   │   ├── transcribe_voice_action.py
│   │   └── protocols/                # IConversationAI, ISystemPromptBuilder, ITranscriber, ...
│   └── handlers/
│       ├── text_message_handler.py
│       ├── clear_command_handler.py  # /clear — AIApplication.clear_context(thread_id)
│       ├── voice_message_handler.py
│       ├── photo_message_handler.py, document_message_handler.py  # фото/PDF — вложениями, текстовые — текстом
│       ├── attachment_limits.py      # лимит Claude на картинку (5 МБ в base64)
│       └── protocols/                # IConversationClearer
├── todoist/                 # TodoistHttpClient (API v1, без close/update/delete), TodoistTaskService
├── gmail/                   # GmailClient (поиск, чтение, черновик ответа — без отправки), UntrustedMailFrame
└── voice_recognition/       # HttpTranscriber, NativeTranscriber
scripts/
└── gmail_auth.py            # Получение refresh token Gmail владельца в pass (standalone, uv run)
data/
├── system_prompt.txt        # Системный промпт ассистента; {today}, {now}, {timezone} подставляются на каждый запрос
├── phrases.json, roles.json, languages.json
deploy/                      # Образ и выкат в colima
```

## Движок: ai_framework

- Зависимость `ai-bot-framework[claude-sdk]` из git по тегу (`[tool.uv.sources]`). `claude-agent-sdk` везёт CLI
  Claude Code бинарём внутри колеса (`claude_agent_sdk/_bundled/claude`), Node не нужен
- Провайдер — `Provider.CLAUDE_SDK` в боте, чекапе и наполнении памяти; модель — `AI_MODEL`. Ключа API нет:
  CLI берёт `CLAUDE_CODE_OAUTH_TOKEN` из окружения, а нативно без него — локальный логин Claude Code.
  Ключ Claude API в окружении процесса держать нельзя: CLI предпочтёт его подписке, и счёт пойдёт по API
- `ClaudeSdkProvider` (v0.9.3) держит сессию CLI на тред; `clear_context` её сбрасывает. Сессии CLI — в `$HOME/.claude`
- Память диалога — `AI_DB_URL`: та же БД `personal_assistant`, схема `ai` (`options=-csearch_path%3Dai`).
  Миграции ai_framework применяются при входе в `with ai:`, но саму схему не создают: `CREATE SCHEMA IF NOT EXISTS ai` — один раз руками
- Тред диалога — `str(user_id)`, в истории последние `HISTORY_TURNS_LIMIT = 10` ходов
- Перед каждым запросом `SendToAgentAction` обновляет системный промпт (`update_system_prompt`) — в нём сегодняшняя дата
  в поясе `OWNER_TIMEZONE`
- `/clear` — `AIApplication.clear_context(thread_id)`: чистит историю треда владельца и (с v0.9.3) сбрасывает
  сессию SDK этого треда. `/context` нет: статистика была у сессии Claude Code
- Зависимость — `ai-bot-framework[claude-sdk,s3]` тега `v0.9.3` (v0.9.2 не брать)
- Все хендлеры — только роль `admin`

## Инструменты (tools)

Точка регистрации одна — список `tools` в `workers/bot/__main__.py`, он передаётся в `AIApplication`.
`ClaudeSdkProvider` отдаёт их CLI как SDK MCP-сервер `ai-framework-tools`: модель видит `mcp__ai-framework-tools__<name>`.

### Встроенные инструменты CLI выключены

`deploy/claude-code/managed-settings.json` кладётся в образ как `/etc/claude-code/managed-settings.json`
(root, uid 1000 его не перепишет). Managed settings грузятся всегда, независимо от `setting_sources`:

- `permissions.deny` — все встроенные инструменты CLI поимённо: запрещённый инструмент убирается из контекста модели
- `PreToolUse`-хук на всё — страховка на инструмент, которого нет в списке (новая версия CLI): пропускает только
  `mcp__ai-framework-tools__*`, остальное блокирует
- `allowedMcpServers` — только `ai-framework-tools`; `allowManaged{PermissionRules,Hooks}Only` — правила и хуки
  пользователя и проекта не действуют. `ENABLE_CLAUDEAI_MCP_SERVERS=false` в образе — без коннекторов claude.ai

Нативно `/etc/claude-code` (на macOS `/Library/Application Support/ClaudeCode`) — это собственный Claude Code
владельца, поэтому проверочные скрипты подключают тот же файл как project settings временного каталога:

- `uv run python -m scripts.claude_cli_tools_check` — список инструментов из init CLI, без вызова модели;
  в образе: `docker run --rm -v "$PWD/scripts:/app/scripts:ro" --entrypoint python personal_assistant-bot:latest -m scripts.claude_cli_tools_check`.
  Должно быть ровно `mcp__ai-framework-tools__…`
- `uv run python -m scripts.claude_sdk_live_check bot|checkup` — живой прогон `AIApplication(CLAUDE_SDK)` со
  списком инструментов бота или чекапа на локальных подменах источников, вызовы модели настоящие

Обновил `claude-agent-sdk` в `uv.lock` — прогони `claude_cli_tools_check`: новый инструмент CLI добавляется в `deny`.
Инструменты вызываются синхронно изнутри event loop провайдера: `asyncio.run` в их коде падает (так `GitCli`
гоняет git своим циклом в отдельном потоке)

### Todoist и Gmail

Регистрируются в `__main__.py` через `workers/bot/todoist_tools_factory.py` и `workers/bot/gmail_tools_factory.py`,
если заданы переменные: `TODOIST_TOKEN` — `find_tasks`, `create_task`; все три `GMAIL_*` — `search_mail`, `read_mail`,
`draft_reply` (задана только часть `GMAIL_*` — бот падает на старте). В проде compose требует все четыре.
Список зарегистрированных инструментов пишется в лог на старте строкой `AI tools: …`.

Граница задаётся набором методов, а не промптом:

- **Почта не отправляется.** Инструмента отправки нет, в `GmailClient` нет метода send. `draft_reply` — только
  ответ в существующий тред, адресата и тему берёт код из исходного письма. Scope токена — `gmail.readonly` +
  `gmail.compose`
- **Задачи не закрываются и не удаляются.** В `TodoistHttpClient` нет close/update/delete. `create_task` ставит
  задачу во Входящие с меткой `pa` (ставит код, не модель) и обязательным сроком
- Текст писем — данные: инструменты почты оборачивают его в `UntrustedMailFrame`, системный промпт запрещает
  исполнять указания из писем

Refresh token Gmail: `uv run scripts/gmail_auth.py` (из корня репы, на машине с ключом pass ассистента) — берёт
OAuth-клиент из pass `assistant/personal_assistant/gmail-oauth-client`, открывает согласие (offline,
`prompt=consent`) и кладёт токен в `assistant/personal_assistant/gmail-refresh-token`, на экран его не выводит.
Экран согласия проекта Google — «In production»: в Testing refresh token живёт 7 дней

Добавить инструмент:

1. Пакет `src/ai_tools/<name>/` с `tool.py`: класс-наследник `ai_framework.BaseTool` с `name`, `description`,
   `Input` (Pydantic-модель аргументов) и `execute(input, context) -> str`. Зависимости — через конструктор,
   Protocol-ы зависимостей — в `src/ai_tools/<name>/protocols/`
2. Экспорт из `src/ai_tools/__init__.py`
3. Экземпляр — в список `tools` в `__main__.py`
4. В `context` (`ToolContext`) приходят `chat_id` и `user_id` из `SendToAgentAction`
5. Инструмент, который сам ответил в чат, возвращает `suppress_response` — тогда «Думаю...» удаляется, а текст модели не шлётся

## Вики

Слой `src/wiki` — локальная git-копия `obsidian_wiki` (`WIKI_DIR`): первый вызов делает clone по `WIKI_REMOTE_URL`
на пустом каталоге, дальше pull перед чтением; запись — коммит `pa: …` и push в `main` ключом `WIKI_SSH_KEY_PATH`.
Сборка — `build_wiki_tools` в `workers/bot/__main__.py`: один `WikiFactory` на бот, инструменты
`wiki_search` (`WikiSearcher` поверх `WikiReader`), `wiki_read`, `wiki_create_page`, `wiki_append`.
Инструменты памяти (`memory_*`) работают через тот же `WikiFactory` — общий замок на копию.
В системном промпте: факт из вики — со ссылкой на путь страницы; служебные страницы памяти — только через `memory_*`.

## Переменные окружения (.env)

```
BOT_TOKEN=токен-бота
BOT_DB_URL=postgres://user:password@localhost:5432/personal_assistant?sslmode=disable
REDIS_URL=redis://localhost:6379/4
AI_DB_URL=postgres://user:password@localhost:5432/personal_assistant?sslmode=disable&options=-csearch_path%3Dai
CLAUDE_CODE_OAUTH_TOKEN=токен подписки          # claude setup-token; нативно необязательная — CLI возьмёт локальный логин
AI_MODEL=claude-sonnet-4-5
OWNER_TIMEZONE=Asia/Almaty                      # необязательная (дефолт Asia/Almaty); пояс для даты в системном промпте
VOICE_RECOGNITION_URL=http://localhost:8000     # необязательная (есть дефолт); HTTP-сервис распознавания речи (faster-whisper, GPU)
VOICE_RECOGNITION_API_KEY=ключ                  # заголовок X-API-Key для сервиса распознавания; без него сервис отвечает 401
VOICE_RECOGNITION_MODE=http                     # необязательная (дефолт http); http | native
WHISPER_MODEL=small                             # необязательная (дефолт small); модель для native-режима
LOG_LEVEL=INFO                                  # необязательная (дефолт INFO); логгеры TeleBot/urllib3/requests/httpx/anthropic всегда не ниже WARNING; DEBUG у ai_framework пишет вызовы инструментов
WIKI_DIR=/path/to/obsidian_wiki                 # локальная копия вики; пустой каталог — бот сам сделает clone
WIKI_REMOTE_URL=git@github.com:sumarokov-vp/obsidian_wiki.git
WIKI_SSH_KEY_PATH=/path/to/deploy_key           # необязательная; без неё git берёт ssh-ключи/агент пользователя
DROPBOX_ROOT=/path/to/Dropbox                   # необязательная; без неё инструменты Dropbox не регистрируются
ATTACHMENTS_S3_ENDPOINT=https://fra1.digitaloceanspaces.com   # хранилище вложений (фото, PDF) — DO Spaces
ATTACHMENTS_S3_BUCKET=sumarokov-pa-attachments
ATTACHMENTS_S3_REGION=fra1
ATTACHMENTS_S3_ACCESS_KEY=ключ Spaces
ATTACHMENTS_S3_SECRET_KEY=секрет Spaces
TODOIST_TOKEN=токен                             # необязательная; без неё find_tasks и create_task не регистрируются
GMAIL_CLIENT_ID=id OAuth-клиента                # GMAIL_* — все три или ни одной; без них инструменты почты не регистрируются
GMAIL_CLIENT_SECRET=секрет OAuth-клиента
GMAIL_REFRESH_TOKEN=refresh token владельца     # uv run scripts/gmail_auth.py
```

Обязательны на старте бота: `BOT_TOKEN`, `BOT_DB_URL`, `REDIS_URL`, `AI_DB_URL`, `AI_MODEL`, `WIKI_DIR`,
`WIKI_REMOTE_URL`, `ATTACHMENTS_S3_*`. `TODOIST_TOKEN` и `GMAIL_*` в коде бота необязательны (нет — нет инструментов),
в проде их требует compose. Их же читают `workers.checkup` (`TODOIST_TOKEN` обязателен) и `workers.memory_fill` (`GMAIL_*` необязательны)

## Распознавание речи

Два взаимозаменяемых транскрайбера, выбор через `VOICE_RECOGNITION_MODE` (сборка в `workers/bot/transcriber_factory.py`):

- `http` (по умолчанию) — `HttpTranscriber`, внешний GPU-сервис по `VOICE_RECOGNITION_URL`. Основной путь, никаких тяжёлых зависимостей.
  Сервис требует заголовок `X-API-Key` (`VOICE_RECOGNITION_API_KEY`), без ключа открыт только `GET /health`.
- `native` — `NativeTranscriber` на `openai-whisper` в процессе бота. Требует опциональной зависимости:
  `uv sync --extra whisper` (тянет torch + CUDA, ~7 GiB). Без установленного пакета режим падает на старте
  с понятным сообщением, обычный `uv sync` whisper НЕ ставит и в Docker-образ он не попадает.

Импорт `whisper` ленивый (`importlib.import_module` внутри `NativeTranscriber`), поэтому код нативного
транскрайбера импортируется и проверяется линтерами без установленного пакета.

## Вложения: фото и документы

- Фото (Telegram отдаёт JPEG) и документы JPEG/PNG/GIF/WebP/PDF уходят в `process_message(attachments=[Attachment(...)])`,
  модель читает их сама. Текстовые `.txt/.md/.csv` (и `text/*`) декодируются и уходят текстом. Прочее — «Такой формат
  пока не читаю.» без вызова AI
- Лимиты — в composition root: `MAX_ATTACHMENT_BYTES` 10 МБ на любой файл, `MAX_IMAGE_BYTES` 5 МБ на картинку в base64
  (≈3.75 МБ сырых байт — лимит Claude). Сверх — отказ сообщением, без скачивания и без AI
- Байты вложений — в DO Spaces (`S3AttachmentStore`, бакет `sumarokov-pa-attachments`, fra1), в истории ai_framework
  (`ai_messages.attachments`) — только ключи. `AIApplication` сам оборачивает хранилище в `CachedAttachmentStore`.
  На диск бота ничего не пишется. Объекты бакета библиотека не удаляет — `/clear` чистит историю, не бакет
- `dropbox_save` (`src/ai_tools/dropbox_save/`) берёт вложение из истории треда `str(user_id)`: `PostgresMemoryStore(AI_DB_URL)`
  читает `ai_messages`, байты — тот же `S3AttachmentStore`, что у `AIApplication`. Окно — последние `HISTORY_TURNS_LIMIT`
  ходов. Пишет `DropboxFileSaver` (граница `DropboxBoundary` + журнал `dropbox_journal`, action `added`); перезаписи нет —
  « (2)». Регистрируется при `DROPBOX_ROOT`. Текстовые `.txt/.md/.csv` в S3 не попадают — их `dropbox_save` не сохранит

## Технологический стек

- Python 3.13+
- bot-framework[all]==0.8.2 — фреймворк для Telegram-ботов
- ai-bot-framework[claude-sdk,s3] (git-тег v0.9.3) — AIApplication, память, ClaudeSdkProvider, вложения в S3
- uv — управление зависимостями

## Команды

- Установка зависимостей: `uv sync`
- Запуск бота: `uv run python -m workers.bot`
- Проверки: `uv run ruff check .`, `uv run mypy src workers tests`, `uv run lint-imports`, `uv run pytest`

## Deploy

- Бот работает контейнером в colima на Mac mini (linux/arm64). В образе CLI Claude Code из колеса
  `claude-agent-sdk` со встроенными инструментами, выключенными managed settings (см. выше); git и openssh-client —
  для вики, ключи хоста github.com — из `deploy/ssh/known_hosts` (системный known_hosts); typst и jq нет.
  Деплой — `deploy/up.sh` (скилл `/deploy`), локально, без SSH
- `up.sh` берёт секреты из pass (`assistant/personal_assistant/{bot-token,db,claude-oauth-token,voice-recognition-key,obsidian-wiki-deploy-key,spaces-attachments,todoist-token,gmail-oauth-client,gmail-refresh-token}`,
  `GNUPGHOME=~/docker/personal_assistant/gnupg` — свой GPG-ключ ассистента), собирает из `db` переменную
  `AI_DB_URL` (`options=-csearch_path%3Dai`), разбирает `spaces-attachments` (первая строка — secret key → `ATTACHMENTS_S3_SECRET_KEY`,
  строки `access_key=`, `bucket=`, `region=`, `endpoint=` → остальные `ATTACHMENTS_S3_*`), из `gmail-oauth-client`
(JSON `client_secret_*.json` целиком) достаёт `installed.client_id`/`installed.client_secret` через `python3` → `GMAIL_CLIENT_ID`/`GMAIL_CLIENT_SECRET`,
первые строки `todoist-token` и `gmail-refresh-token` → `TODOIST_TOKEN`, `GMAIL_REFRESH_TOKEN`, и запускает `docker compose -f deploy/compose.yaml up -d --build`.
  Секреты идут переменными окружения, в файлы не пишутся — кроме deploy-ключа вики: ssh читает ключ только из
  файла, `up.sh` кладёт его в `~/docker/personal_assistant/secrets/wiki_deploy_key` (0600, каталог 0700), в
  контейнер он монтируется read-only как `/run/secrets/wiki_deploy_key` (`WIKI_SSH_KEY_PATH`)
- Вики: том `~/docker/personal_assistant/wiki` → `/wiki`, `WIKI_DIR=/wiki/obsidian_wiki`; первый clone на пустом
  томе делает сам бот. `WIKI_REMOTE_URL` — `git@github.com:sumarokov-vp/obsidian_wiki.git` (дефолт в compose/up.sh)
- Схему `ai` в БД `personal_assistant` `up.sh` не создаёт — `CREATE SCHEMA IF NOT EXISTS ai` делается один раз
  руками (`docker exec -u postgres postgres psql -U sumarokov -d personal_assistant`), миграции ai_framework её не создают
- Сеть — внешняя `infra`: `postgres`, `redis` по именам. `network_mode: host` в colima указывал бы на Linux-VM, а не на mac
- Распознавание речи — GPU-сервер по mesh `http://10.72.0.199:8000`, из контейнера достижим
- Dropbox: `~/Dropbox` хоста (синхронизирует Maestral на Mac mini) — том `/dropbox` на запись, `DROPBOX_ROOT=/dropbox`.
  colima отдаёт `$HOME` через virtiofs (`~/.colima/default/colima.yaml`: `mounts: []`), файл из контейнера ложится
  на хост под владельцем, и Maestral его подхватывает как обычную правку. Закрытые папки перекрыты пустым каталогом
  `~/docker/personal_assistant/empty` только на чтение — их содержимого в контейнере нет физически: `Vault`,
  `03_home/07_ecp/egov.kz` (ключи ЭЦП и пароль). `01_work` открыт (решение владельца 26.09.2026). Заглушку создаёт `up.sh` и падает, если она не пуста.
  Новая чувствительная папка в корне Dropbox видна боту, пока её не добавят в оверлеи `compose.yaml`;
  `vault_selftest_*` меняют имена — их отсекает код инструментов Dropbox, не монтирование
- В контейнере uid 1000; монтируются том вики, ключ вики и Dropbox: сессии CLI живут в `$HOME/.claude` контейнера
  и пропадают с ним
- `docker compose build` без `up.sh` требует заглушки секретов, compose интерполирует `${VAR:?}` и при сборке:
  `TODOIST_TOKEN=x GMAIL_CLIENT_ID=x GMAIL_CLIENT_SECRET=x GMAIL_REFRESH_TOKEN=x BOT_TOKEN=x BOT_DB_URL=x AI_DB_URL=x CLAUDE_CODE_OAUTH_TOKEN=x VOICE_RECOGNITION_API_KEY=x PA_DATA_DIR=x WIKI_DEPLOY_KEY_FILE=x ATTACHMENTS_S3_ENDPOINT=x ATTACHMENTS_S3_BUCKET=x ATTACHMENTS_S3_REGION=x ATTACHMENTS_S3_ACCESS_KEY=x ATTACHMENTS_S3_SECRET_KEY=x DROPBOX_DIR=x docker compose -f deploy/compose.yaml build`.
  Эта команда перетегирует `personal_assistant-bot:latest`; проверить сборку, не задевая прод, — `docker build -f deploy/Dockerfile -t <свой тег> .`
- Одна копия бота на Telegram-токен: нативный запуск и контейнер одновременно не держать
- Redis база: 4
