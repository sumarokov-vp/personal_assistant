---
name: deploy
description: Деплой бота. Запускает линтеры, тесты, собирает Docker-образ и перезапускает контейнер.
allowed-tools: Bash(.claude/skills/deploy/scripts/*)
---

Запусти скрипт деплоя:

```bash
.claude/skills/deploy/scripts/deploy.sh
```

Дождись завершения и сообщи результат пользователю.
