# Personal Assistant Bot

Telegram-бот — персональный ассистент владельца. Текст владельца уходит в `ai_framework` (Claude API по
`ANTHROPIC_API_KEY`), ответ модели возвращается в чат. У модели нет Bash и доступа к файловой системе:
она действует только через инструменты, объявленные в коде бота.

## Архитектура

```
Telegram <-> bot_framework <-> SendToAgentAction <-> ai_framework.AIApplication <-> Claude API
                                                          |
                                                          +-- память диалога: Postgres, схема ai
```

### Структура проекта

```
workers/bot/
├── __main__.py              # Composition root: env, AIApplication, список tools, сборка хендлеров
└── transcriber_factory.py   # Выбор транскрайбера по VOICE_RECOGNITION_MODE
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
│       ├── voice_message_handler.py, photo_message_handler.py, document_message_handler.py
│       └── protocols/                # IConversationClearer
└── voice_recognition/       # HttpTranscriber, NativeTranscriber
data/
├── system_prompt.txt        # Системный промпт ассистента; {today}, {now}, {timezone} подставляются на каждый запрос
├── phrases.json, roles.json, languages.json
deploy/                      # Образ и выкат в colima
```

## Движок: ai_framework

- Зависимость `ai-bot-framework` из git по тегу (`[tool.uv.sources]`), **без extra `claude-sdk`**:
  `claude_agent_sdk` в окружении и в образе быть не должно (`grep -r claude_agent_sdk src workers uv.lock` пуст)
- Провайдер — `Provider.ANTHROPIC`, модель — `AI_MODEL`, ключ — `ANTHROPIC_API_KEY`
- Память диалога — `AI_DB_URL`: та же БД `personal_assistant`, схема `ai` (`options=-csearch_path%3Dai`).
  Миграции ai_framework применяются при входе в `with ai:`, но саму схему не создают: `CREATE SCHEMA IF NOT EXISTS ai` — один раз руками
- Тред диалога — `str(user_id)`, в истории последние `HISTORY_TURNS_LIMIT = 10` ходов
- Перед каждым запросом `SendToAgentAction` обновляет системный промпт (`update_system_prompt`) — в нём сегодняшняя дата
  в поясе `OWNER_TIMEZONE`
- `/clear` чистит тред владельца. `/context` нет: статистика была у сессии Claude Code
- Все хендлеры — только роль `admin`

## Инструменты (tools)

Точка регистрации одна — список `tools` в `workers/bot/__main__.py`, он передаётся в `AIApplication`.

Добавить инструмент:

1. Пакет `src/ai_tools/<name>/` с `tool.py`: класс-наследник `ai_framework.BaseTool` с `name`, `description`,
   `Input` (Pydantic-модель аргументов) и `execute(input, context) -> str`. Зависимости — через конструктор,
   Protocol-ы зависимостей — в `src/ai_tools/<name>/protocols/`
2. Экспорт из `src/ai_tools/__init__.py`
3. Экземпляр — в список `tools` в `__main__.py`
4. В `context` (`ToolContext`) приходят `chat_id` и `user_id` из `SendToAgentAction`
5. Инструмент, который сам ответил в чат, возвращает `suppress_response` — тогда «Думаю...» удаляется, а текст модели не шлётся

## Переменные окружения (.env)

```
BOT_TOKEN=токен-бота
BOT_DB_URL=postgres://user:password@localhost:5432/personal_assistant?sslmode=disable
REDIS_URL=redis://localhost:6379/4
AI_DB_URL=postgres://user:password@localhost:5432/personal_assistant?sslmode=disable&options=-csearch_path%3Dai
ANTHROPIC_API_KEY=ключ Claude API
AI_MODEL=claude-sonnet-4-5
OWNER_TIMEZONE=Asia/Almaty                      # необязательная (дефолт Asia/Almaty); пояс для даты в системном промпте
VOICE_RECOGNITION_URL=http://localhost:8000     # необязательная (есть дефолт); HTTP-сервис распознавания речи (faster-whisper, GPU)
VOICE_RECOGNITION_API_KEY=ключ                  # заголовок X-API-Key для сервиса распознавания; без него сервис отвечает 401
VOICE_RECOGNITION_MODE=http                     # необязательная (дефолт http); http | native
WHISPER_MODEL=small                             # необязательная (дефолт small); модель для native-режима
LOG_LEVEL=INFO                                  # необязательная (дефолт INFO); логгеры TeleBot/urllib3/requests/httpx/anthropic всегда не ниже WARNING
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
- ai-bot-framework (git-тег, без extra claude-sdk) — AIApplication, память, tool loop
- uv — управление зависимостями

## Команды

- Установка зависимостей: `uv sync`
- Запуск бота: `uv run python -m workers.bot`
- Проверки: `uv run ruff check .`, `uv run mypy src workers tests`, `uv run lint-imports`, `uv run pytest`

## Deploy

- Бот работает контейнером в colima на Mac mini (linux/arm64), без Claude Code: образ не содержит
  `claude_agent_sdk`, typst, git, jq — только рантайм бота. Деплой — `deploy/up.sh` (скилл `/deploy`), локально, без SSH
- `up.sh` берёт секреты из pass (`assistant/personal_assistant/{bot-token,db,anthropic-api-key,voice-recognition-key}`,
  `GNUPGHOME=~/docker/personal_assistant/gnupg` — свой GPG-ключ ассистента), собирает из `db` переменную
  `AI_DB_URL` (`options=-csearch_path%3Dai`) и запускает `docker compose -f deploy/compose.yaml up -d --build`.
  В файлы секреты не пишутся
- Схему `ai` в БД `personal_assistant` `up.sh` не создаёт — `CREATE SCHEMA IF NOT EXISTS ai` делается один раз
  руками (`docker exec -u postgres postgres psql -U sumarokov -d personal_assistant`), миграции ai_framework её не создают
- Сеть — внешняя `infra`: `postgres`, `redis` по именам. `network_mode: host` в colima указывал бы на Linux-VM, а не на mac
- Распознавание речи — GPU-сервер по mesh `http://10.72.0.199:8000`, из контейнера достижим
- В контейнере uid 1000, монтирований нет — `workspace/` и `claude-home` из выката убраны вместе с Claude Code
- `docker compose build` без `up.sh` требует заглушки секретов, compose интерполирует `${VAR:?}` и при сборке:
  `BOT_TOKEN=x BOT_DB_URL=x AI_DB_URL=x ANTHROPIC_API_KEY=x VOICE_RECOGNITION_API_KEY=x docker compose -f deploy/compose.yaml build`
- Одна копия бота на Telegram-токен: нативный запуск и контейнер одновременно не держать
- Redis база: 4
