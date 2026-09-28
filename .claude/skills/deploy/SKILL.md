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
1. берёт секреты из `pass` (`assistant/personal_assistant/{bot-token,owner-telegram-id,db,claude-oauth-token,voice-recognition-key,obsidian-wiki-deploy-key,spaces-attachments,todoist-token,gmail-oauth-client,gmail-refresh-token,rabbitmq,cases-api-key,whatsapp-web}`,
   `GNUPGHOME=~/docker/personal_assistant/gnupg` — свой GPG-ключ ассистента, без пароля), экспортирует
   их только в своё окружение и не печатает;
2. собирает `AI_DB_URL` из `db` (та же БД `personal_assistant`, `options=-csearch_path%3Dai`);
   из `spaces-attachments` (хранилище фото и PDF в DO Spaces) — `ATTACHMENTS_S3_SECRET_KEY` из первой строки и
   `ATTACHMENTS_S3_{ACCESS_KEY,BUCKET,REGION,ENDPOINT}` из строк `access_key=`, `bucket=`, `region=`, `endpoint=`;
   нет какого-то поля — скрипт останавливается до сборки;
   `CASES_API_KEY` — первая строка `cases-api-key`, ключ ассистента к сервису кейсов `assistant_cases` (контейнер
   в сети `infra`, `CASES_API_URL` по умолчанию `http://assistant_cases:8000`); тот же ключ должен быть строкой
   `user:ключ` в `API_KEYS` сервиса кейсов, иначе инструменты кейсов получат 401;
3. кладёт deploy-ключ вики файлом 0600 в `~/docker/personal_assistant/secrets/wiki_deploy_key` (ssh берёт
   ключ только из файла; в контейнер он монтируется read-only) и заводит том вики
   `~/docker/personal_assistant/wiki` — первый clone `obsidian_wiki` на пустом томе делает сам бот;
4. запускает `hosts/whatsapp_web/install.sh` — хостовый сервис WhatsApp Web (launchd-агент
   `com.sumarokov.personal-assistant.whatsapp-web`, не в контейнере, слушает `127.0.0.1:18790`):
   копирует проект в постоянный `~/docker/personal_assistant/whatsapp-web/app` (`rsync
   --checksum`, не сам checkout — `ProgramArguments` в plist смотрит туда, поэтому удаление или
   переключение ветки рабочей копии сервис не ломает) и там же `uv sync --locked --no-dev`;
   ключ и номер — pass `whatsapp-web` (первая строка ключ, `phone=`; нет записи — заводит сам),
   учётка RabbitMQ `agent-whatsapp-web` — `deploy/rabbitmq/setup.sh add-source whatsapp-web`.
   `WHATSAPP_WEB_TOKEN` в шаге 1 — та же первая строка `whatsapp-web`, боту нужен тот же ключ;
5. выполняет `docker compose -f deploy/compose.yaml up -d --build`.

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
