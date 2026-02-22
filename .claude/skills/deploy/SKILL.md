---
name: deploy
description: Деплой проекта. Требует агента devops для выполнения.
allowed-tools: Bash(.claude/skills/deploy/scripts/*)
---

Делегируй выполнение деплоя агенту **devops**.

Деплой локальный — бот работает на этой машине. Docker Compose запускается локально.

Агент devops должен выполнить:

```
python .claude/skills/deploy/scripts/deploy.py
```

Скрипт выполняет три шага:
1. `docker compose build` — сборка образа
2. `docker compose down` — остановка текущих контейнеров
3. `docker compose up -d` — запуск новых контейнеров

Compose-файл: `deploy/docker-compose.yml`

После завершения — сообщи пользователю результат (успех или ошибку с кодом выхода).
