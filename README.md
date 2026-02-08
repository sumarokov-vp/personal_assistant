# Personal Assistant Bot

Telegram-бот — персональный ассистент. Принимает текстовые сообщения, отправляет их в Claude Agent SDK и возвращает ответы обратно в Telegram.

```
Telegram User <-> bot-framework <-> Claude Agent SDK <-> Claude API
```

## Стек

- Python 3.13+
- [bot-framework](https://github.com/smartist-org/bot-framework) — фреймворк для Telegram-ботов (pyTelegramBotAPI)
- [claude-agent-sdk](https://www.npmjs.com/package/@anthropic-ai/claude-agent-sdk) — Claude Agent SDK
- PostgreSQL + Redis
- Docker для деплоя
- uv для управления зависимостями

## Установка

```bash
# Клонировать репозиторий
git clone <repo-url>
cd personal_assistent

# Установить зависимости
uv sync

# Создать .env из шаблона
cp .env.example .env
```

Заполнить `.env`:

```
BOT_TOKEN=токен-бота
BOT_DB_URL=postgres://user:password@localhost:5432/personal_assistant?sslmode=disable
REDIS_URL=redis://localhost:6379/4
```

## Требования

- PostgreSQL — база данных для бота
- Redis — кеширование
- Активная подписка Claude Code — SDK авторизуется через `~/.claude/session-env`, отдельный API-ключ не нужен

## Запуск

```bash
uv run python -m workers.bot
```

## Деплой (Docker)

```bash
deploy/deploy.sh
```

Docker Compose монтирует `~/.claude:ro` (read-only) для доступа к сессии Claude Code.

## Кастомные инструменты (Tool Use)

Бот поддерживает кастомные инструменты через MCP-сервер. Claude может вызывать их во время обработки запроса.

### send_file

Отправляет файл пользователю в Telegram как документ. Claude может вызвать этот инструмент, когда нужно передать пользователю созданный файл.

## Структура проекта

```
workers/bot/
└── __main__.py                # Точка входа, инициализация
src/
├── agent/
│   ├── client.py              # Обёртка над Claude Agent SDK
│   ├── protocols/
│   │   └── i_agent_client.py  # Интерфейс клиента
│   └── tools/
│       ├── registry.py        # SessionRegistry — контекст сессии для tools
│       └── send_file.py       # Отправка файлов в Telegram
└── chat/
    ├── handlers/
    │   └── text_message_handler.py   # Обработчик текстовых сообщений
    └── actions/
        └── send_to_agent_action.py   # Отправка в SDK и возврат ответа
data/
├── phrases.json               # i18n фразы
├── roles.json                 # Роли (admin)
└── languages.json             # Языки (ru)
tests/                         # Тесты
deploy/                        # Docker-конфигурация
```

## Доступ

Бот доступен только пользователям с ролью `admin`. Управление ролями — через bot-framework.
