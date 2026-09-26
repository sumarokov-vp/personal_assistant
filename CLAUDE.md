# Personal Assistant Bot

Telegram-бот — персональный ассистент. Транслирует сообщения пользователя в Claude Agent SDK и возвращает ответы.

## Архитектура

```
Telegram User <-> bot_framework (pyTelegramBotAPI) <-> Claude Agent SDK <-> Claude API
```

### Структура проекта

```
workers/bot/
├── __main__.py              # Composition root: пути, политика доступа агента, сборка хендлеров
└── transcriber_factory.py   # Выбор транскрайбера по VOICE_RECOGNITION_MODE
src/
├── agent/
│   ├── client.py                  # AgentClient — диалог с ClaudeSDKClient
│   ├── sdk_client_pool.py         # Пул ClaudeSDKClient по user_id
│   ├── agent_options_factory.py   # ClaudeAgentOptions: workspace, песочница, allow/deny-правила
│   ├── tool_permission_gate.py    # can_use_tool: пускает сеть песочницы, остальное отклоняет
│   ├── protocols/
│   └── tools/
│       ├── registry.py                # SessionRegistry — контекст сессии для tools
│       ├── send_file.py               # Tool: отправка файлов в Telegram
│       └── workspace_file_reader.py   # Чтение файла только изнутри workspace/
├── chat/
│   ├── handlers/
│   │   └── text_message_handler.py   # Обработчик текстовых сообщений
│   └── actions/
│       └── send_to_agent_action.py   # Отправка в Claude SDK и возврат ответа
workspace/                   # Рабочая папка агента (cwd). В git только CLAUDE.md
├── CLAUDE.md                # Инструкция персонального ассистента
└── inbox/                   # Входящие фото и документы из Telegram
data/
├── phrases.json             # i18n фразы
├── roles.json               # Роли
└── languages.json           # Языки
deploy/
├── Dockerfile               # Образ linux/arm64: python:3.13-slim + uv sync --frozen по uv.lock
├── compose.yaml             # Контейнер в colima, сеть infra
└── up.sh                    # Секреты из pass → docker compose up -d --build
```

## Claude Agent SDK

- `claude-agent-sdk==0.2.158` (бандлит Claude Code CLI 2.1.280). Ниже 0.2 не опускаться: в бандле старого SDK
  нет `sandbox.failIfUnavailable`, и при сбое песочницы Bash молча шёл бы без неё
- Авторизация — долгоживущий токен подписки `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`), лежит в pass:
  `work/projects/sumarokov/pa/personal_assistant/claude-oauth-token`. `~/.claude/.credentials.json` не используется,
  `ANTHROPIC_API_KEY` не нужен
- Сессии CLI в контейнере — `~/docker/personal_assistant/claude-home` на хосте (хостовый `~/.claude` не монтируется)

### Модель доступа агента

Вся политика собирается в `AgentOptionsFactory`, пути и список секретов задаёт composition root
(`workers/bot/__main__.py`). Два режима:

- **Контейнер (прод, colima)**: граница — сам контейнер. В нём смонтированы только `workspace/` и `claude-home`,
  секретов хоста нет. Песочница Claude Code выключена (`AGENT_SANDBOX=false`): bubblewrap в контейнере colima
  не запускается, нет непривилегированных user namespaces. Bash разрешён правилом `Bash`. Deny-правила,
  gate, ограничения `send_file` и запрет записи в настройки агента действуют как обычно
- **Нативно на macOS** (разработка, `uv run python -m workers.bot`): песочница seatbelt включена по умолчанию,
  подробности ниже

Детали:

- **cwd = `workspace/`** в корне проекта. Инструкция ассистента — `workspace/CLAUDE.md`
- **`setting_sources=["project"]`** — грузится только `workspace/CLAUDE.md` и `workspace/.claude/`.
  Пользовательские `~/.claude/CLAUDE.md`, скиллы, хуки и плагины агенту не видны
- **Песочница Bash (seatbelt, только при `AGENT_SANDBOX` ≠ `false`)**: `enabled`, `failIfUnavailable` (без песочницы CLI не стартует),
  `allowUnsandboxedCommands=false` (флаг `dangerouslyDisableSandbox` игнорируется), `excludedCommands=[]`.
  Запись только в `workspace/`, сеть открыта
- **Закрытые пути** (чтение и запись, и в Bash, и во встроенных Read/Edit/Write/Glob/Grep; список — `agent_protected_paths()`):
  `~/.password-store`, `~/.local/share/password-store`, `~/.gnupg`, `~/.ssh`, `~/Vault`, `/Volumes/Vault`,
  `~/.claude/.credentials.json`, `~/.claude/projects`, `~/.claude/history.jsonl`, `~/.config`, `~/.aws`, `~/.docker`,
  `~/.netrc`, `~/.kube`, `~/.colima`, `~/.lima`, `~/Library/Keychains`, `.env` бота.
  Ограничения действуют на инструменты агента, а не на процесс CLI: сам CLI читает `~/.claude` как обычно
- **Настройки агента в workspace** (`.claude/`, `.mcp.json`, `CLAUDE.md`, `CLAUDE.local.md`) агенту на запись закрыты:
  через них он мог бы ослабить себе права или завести хук, который выполняется вне песочницы
- **Переменные окружения бота** (`BOT_TOKEN`, `BOT_DB_URL`, `REDIS_URL`, `VOICE_RECOGNITION_API_KEY` и все ключи `.env`)
  передаются CLI пустыми — из Bash их не прочитать
- **`CLAUDE_CODE_OAUTH_TOKEN`** нужен самому CLI, поэтому пустым не передаётся. Из окружения Bash и других
  подпроцессов его вычищает CLI (`CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1`)
- **Процесс бота на Linux недампабельный** (`PR_SET_DUMPABLE=0`): без песочницы Bash агента работает под тем же uid
  и иначе прочитал бы секреты из `/proc/<pid бота>/environ`
- **Режим разрешений `default`** с явными правилами в `--settings`:
  - allow: `Read`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, `TodoWrite`, `Task`, `Agent`, `Edit/Write/NotebookEdit` только в `workspace/**`, `mcp__bot-tools`,
    плюс MCP-серверы из `AGENT_ALLOWED_MCP_SERVERS` (`workers/bot/__main__.py`) — единственное место, где открываются коннекторы
  - **Временно** открыты коннекторы claude.ai Gmail и Google Calendar (`mcp__claude_ai_Gmail`, `mcp__claude_ai_Google_Calendar`,
    все их инструменты). Остальные коннекторы (Drive, Slack, Docs и пр.) закрыты: решение по ним не принято
  - Bash разрешается автоматически, потому что работает в песочнице (`autoAllowBashIfSandboxed`)
  - всё, что упирается в запрос разрешения, приходит в `ToolPermissionGate` (`can_use_tool`). Он пропускает
    `SandboxNetworkAccess` (сетевые запросы из песочницы) и отклоняет остальное с объяснением. Интерактива нет,
    бот на запросах не зависает
  - `bypassPermissions` отключён (`disableBypassPermissionsMode`). В нём `Write` мог писать куда угодно, кроме
    явно закрытых путей, например в `~/.zshrc` или `~/Library/LaunchAgents`. В `dontAsk` CLI молча отклоняет
    сетевые запросы песочницы
- **`send_file`** выполняется в процессе бота, вне песочницы, поэтому сам проверяет путь (`WorkspaceFileReader`).
  Путь резолвится, `..` и симлинки наружу отклоняются, а реальный путь уже открытого дескриптора сверяется
  с `workspace/` (защита от подмены симлинка между проверкой и чтением)
- Входящие фото и документы сохраняются в `workspace/inbox/`. Голосовые — во временную папку системы:
  их читает только транскрайбер в процессе бота, после распознавания файл удаляется
- `TranscriptCleaner` запускает отдельный `query` с `cwd=workspace/`, без инструментов и без настроек

## Переменные окружения (.env)

```
BOT_TOKEN=токен-бота
BOT_DB_URL=postgres://user:password@localhost:5432/personal_assistant?sslmode=disable
REDIS_URL=redis://localhost:6379/4
VOICE_RECOGNITION_URL=http://localhost:8000     # необязательная (есть дефолт); HTTP-сервис распознавания речи (faster-whisper, GPU)
VOICE_RECOGNITION_API_KEY=ключ                  # заголовок X-API-Key для сервиса распознавания; без него сервис отвечает 401
VOICE_RECOGNITION_MODE=http                     # необязательная (дефолт http); http | native
WHISPER_MODEL=small                             # необязательная (дефолт small); модель для native-режима
AGENT_SANDBOX=true                              # необязательная (дефолт true); false — без песочницы Claude Code (в контейнере)
LOG_LEVEL=INFO                                  # необязательная (дефолт INFO); логгеры TeleBot/urllib3/requests всегда не ниже WARNING — на DEBUG они пишут URL Telegram API с токеном бота
```

## Распознавание речи

Два взаимозаменяемых транскрайбера, выбор через `VOICE_RECOGNITION_MODE` (сборка в `workers/bot/transcriber_factory.py`):

- `http` (по умолчанию) — `HttpTranscriber`, внешний GPU-сервис по `VOICE_RECOGNITION_URL`. Основной путь, никаких тяжёлых зависимостей.
  Сервис требует заголовок `X-API-Key` (`VOICE_RECOGNITION_API_KEY`), без ключа открыт только `GET /health`.
- `native` — `NativeTranscriber` на `openai-whisper` в процессе бота. Требует опциональной зависимости:
  `uv sync --extra whisper` (тянет torch + CUDA, ~7 GiB). Без установленного пакета режим падает на старте
  с понятным сообщением, обычный `uv sync` whisper НЕ ставит и в Docker-образ он не попадает.

Импорт `whisper` ленивый (`importlib.import_module` внутри `NativeTranscriber`), поэтому код нативного
транскрайбера импортируется и проверяется линтерами без установленного пакета.

## Технологический стек

- Python 3.13+
- bot-framework[all]==0.8.2 — фреймворк для Telegram-ботов
- claude-agent-sdk==0.2.158 — Claude Agent SDK
- uv — управление зависимостями

## Команды

- Установка зависимостей: `uv sync`
- Добавить пакет: `uv add <lib>`
- Запуск бота: `uv run python -m workers.bot`

## Deploy

- Бот работает контейнером в colima на Mac mini (linux/arm64). Деплой — `deploy/up.sh` (скилл `/deploy`), локально, без SSH
- `up.sh` берёт секреты из pass (`work/projects/sumarokov/pa/personal_assistant/{bot-token,db,claude-oauth-token}`,
  ключ `personal_assistant` из первой строки `work/projects/internal/infrastructure/voice_recognition/api-keys`),
  экспортирует их и запускает `docker compose -f deploy/compose.yaml up -d --build`. В файлы секреты не пишутся
- Сеть — внешняя `infra`: `postgres`, `redis` по именам. `network_mode: host` в colima указывал бы на Linux-VM, а не на mac
- Распознавание речи — GPU-сервер по mesh `http://10.72.0.199:8000`, из контейнера достижим
- Монтирования: `workspace/` → `/app/workspace`, `~/docker/personal_assistant/claude-home` → `/home/sumarokov/.claude`.
  В контейнере uid 1000; virtiofs colima пишет на хост под uid владельца, права на хосте не нужны
- `docker compose build` без `up.sh` требует заглушки секретов, compose интерполирует `${VAR:?}` и при сборке:
  `BOT_TOKEN=x BOT_DB_URL=x VOICE_RECOGNITION_API_KEY=x CLAUDE_CODE_OAUTH_TOKEN=x docker compose -f deploy/compose.yaml build`
- Одна копия бота на Telegram-токен: нативный запуск и контейнер одновременно не держать
- Redis база: 4

## Tool Use (кастомные инструменты)

Claude Agent SDK поддерживает кастомные инструменты через MCP-сервер. Инструменты позволяют LLM выполнять действия в контексте Telegram-бота.

### Архитектура

- `SessionRegistry` хранит контекст сессии (chat_id, bot instance) по user_id
- Перед каждым query контекст устанавливается через `set_context()`
- Tool-функции получают контекст через `get_current_context()`
- MCP-сервер создаётся один раз в `__main__.py` и передаётся в `AgentOptionsFactory`

### Доступные инструменты

- **send_file** — отправляет файл пользователю в Telegram как документ. Принимает `file_path`: абсолютный путь или путь
  относительно `workspace/`. Файлы вне `workspace/` отклоняются (`PermissionError` → ошибка инструмента агенту).

### Добавление нового инструмента

1. Создать файл `src/agent/tools/my_tool.py`
2. Определить async-функцию с декоратором `@tool(name, description, input_schema)`
3. Добавить `init_*()` для инициализации (передача registry)
4. Зарегистрировать в MCP-сервере в `workers/bot/__main__.py`
5. Инструмент выполняется в процессе бота вне песочницы. Всё, что он читает или пишет на диске, ограничивать `workspace/` самому
6. Ошибку инструмент выбрасывает исключением: SDK вернёт её агенту как `is_error`-результат

## MVP Scope

- Приём текстовых сообщений от пользователя в Telegram
- Трансляция текста в Claude Agent SDK
- Возврат ответа Claude обратно в Telegram
- Авторизация через bot_framework (роли)
- /start меню через bot_framework
- Отправка файлов пользователю через send_file tool
