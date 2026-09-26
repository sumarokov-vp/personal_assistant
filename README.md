# Personal Assistant Bot

Telegram-бот — персональный ассистент. Текст и голос владельца уходят в `ai_framework`, ответ модели
возвращается в чат. Модель работает через CLI Claude Code по подписке, но встроенные инструменты CLI
выключены: у неё только инструменты, объявленные в коде бота (Dropbox, память, вики, Todoist, Gmail).

```
Telegram <-> bot-framework <-> ai_framework (ClaudeSdkProvider) <-> CLI Claude Code (подписка)
```

## Стек

- Python 3.13+
- [bot-framework](https://github.com/smartist-org/bot-framework) — фреймворк для Telegram-ботов
- [ai-bot-framework](https://github.com/sumarokov-vp/ai_bot_framework) с extra `claude-sdk` — AIApplication,
  память диалога, `ClaudeSdkProvider`; CLI Claude Code приезжает бинарём внутри колеса `claude-agent-sdk`
- PostgreSQL + Redis
- uv, Docker (colima)

## Установка

```bash
uv sync
cp .env.example .env
```

Переменные окружения — в `CLAUDE.md`, раздел «Переменные окружения». Движку нужен
`CLAUDE_CODE_OAUTH_TOKEN` (токен подписки, `claude setup-token`); нативно без него CLI берёт локальный
логин Claude Code. Ключ Claude API в окружении не задавать: CLI предпочтёт его подписке.

## Запуск

```bash
uv run python -m workers.bot
```

## Деплой

`deploy/up.sh` (скилл `/deploy`) — сборка и запуск контейнера в colima, секреты из `pass`.

## Проверка, что модели доступны только инструменты бота

```bash
uv run python -m scripts.claude_cli_tools_check         # список инструментов CLI, без вызова модели
uv run python -m scripts.claude_sdk_live_check bot      # живой прогон с инструментами бота
```

## Доступ

У бота один собеседник — владелец, его Telegram ID задаётся в `OWNER_TELEGRAM_ID` (без него или
не числом бот не стартует). Пропускаются только сообщения и нажатия кнопок владельца в личном чате,
остальные апдейты — посторонние, группы, inline, правки — отбрасываются молча, раньше базы и
обработчиков; в лог — строка с типом апдейта, id отправителя и чата, без содержимого.
Роль `admin` в обработчиках остаётся вторым слоем. `/request_role` бот не регистрирует.
