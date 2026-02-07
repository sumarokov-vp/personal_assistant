# Personal Assistant Bot

Telegram-бот — персональный ассистент. Транслирует сообщения пользователя в Claude Agent SDK и возвращает ответы.

## Архитектура

```
Telegram User <-> bot_framework (pyTelegramBotAPI) <-> Claude Agent SDK <-> Claude API
```

### Структура проекта

```
workers/bot/
├── __main__.py              # Точка входа, инициализация BotApplication
└── repo_collection.py       # Коллекция репозиториев (DI)
src/
├── agent/
│   ├── client.py            # Обёртка над Claude Agent SDK (query/ClaudeSDKClient)
│   └── protocols/
│       └── i_agent_client.py
├── chat/
│   ├── handlers/
│   │   └── text_message_handler.py   # Обработчик текстовых сообщений
│   └── actions/
│       └── send_to_agent_action.py   # Отправка в Claude SDK и возврат ответа
data/
├── phrases.json             # i18n фразы
├── roles.json               # Роли
└── languages.json           # Языки
deploy/
├── Dockerfile               # Multi-stage build, python:3.13-slim
├── docker-compose.yml       # Bot + зависимости
└── deploy.sh                # Скрипт деплоя на сервер
```

## Claude Agent SDK

- Авторизация через подписку Claude Code (сессии в ~/.claude/session-env)
- Без отдельного ANTHROPIC_API_KEY — SDK использует существующую авторизацию на машине
- cwd для ClaudeAgentOptions: /home/sumarokov
- SDK автоматически подхватывает: CLAUDE.md, skills/, commands/, scripts/, settings.json
- В Docker: volume mount ~/.claude (включая session-env для авторизации)

## Переменные окружения (.env)

```
BOT_TOKEN=токен-бота
BOT_DB_URL=postgres://user:password@localhost:5432/personal_assistant?sslmode=disable
REDIS_URL=redis://localhost:6379/4
```

## Технологический стек

- Python 3.13+
- bot-framework[all]==0.3.0 — фреймворк для Telegram-ботов
- claude-agent-sdk — Claude Agent SDK
- uv — управление зависимостями

## Команды

- Установка зависимостей: `uv sync`
- Добавить пакет: `uv add <lib>`
- Запуск бота: `uv run python -m workers.bot`

## Deploy

- Один сервер, без разделения на dev/prod
- Docker: `deploy/deploy.sh`
- Redis база: 4

## MVP Scope

- Приём текстовых сообщений от пользователя в Telegram
- Трансляция текста в Claude Agent SDK
- Возврат ответа Claude обратно в Telegram
- Авторизация через bot_framework (роли)
- /start меню через bot_framework
