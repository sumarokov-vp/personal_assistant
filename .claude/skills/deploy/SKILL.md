---
name: deploy
description: Деплой бота — сборка и перезапуск контейнера в colima на этой машине через deploy/up.sh.
allowed-tools: Bash(deploy/up.sh), Bash(docker ps:*), Bash(docker logs:*)
---

Деплой локальный: бот работает контейнером в colima на этом Mac mini. Агент devops и SSH не нужны,
скрипт запускается прямо из корня проекта:

```
deploy/up.sh
```

Скрипт:
1. берёт секреты из `pass` (`assistant/personal_assistant/{bot-token,db,claude-oauth-token,voice-recognition-key}`,
   `GNUPGHOME=~/docker/personal_assistant/gnupg` — свой GPG-ключ ассистента, без пароля), экспортирует
   их только в своё окружение, никуда не пишет и не печатает;
2. собирает `AI_DB_URL` из `db` (та же БД `personal_assistant`, `options=-csearch_path%3Dai`);
3. выполняет `docker compose -f deploy/compose.yaml up -d --build`.

Если `pass` просит GPG-пин — это ожидаемо, дождись пользователя.

После запуска проверь, что контейнер жив и бот стартовал:

```
docker ps --filter name=personal_assistant_bot
docker logs --tail 50 personal_assistant_bot
```

В логах должно быть `Starting polling...` без трейсбека. Секреты из логов не пересказывай.
Сообщи пользователю результат: успех или ошибку с выводом скрипта.

Одновременно может работать только одна копия бота на один Telegram-токен — перед деплоем убедись,
что бот не запущен где-то ещё (например, нативно через `uv run python -m workers.bot`).
