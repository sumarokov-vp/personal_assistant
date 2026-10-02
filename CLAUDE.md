# Personal Assistant Bot

Telegram-бот — персональный ассистент владельца. Текст владельца уходит в `ai_framework`
(`ClaudeSdkProvider` — CLI Claude Code по подписке, `CLAUDE_CODE_OAUTH_TOKEN`), ответ модели возвращается в чат.
У модели нет Bash и доступа к файловой системе: встроенные инструменты CLI выключены, она действует только
через инструменты, объявленные в коде бота (файлы — только через рабочую папку бота и `file_*`, см. «Файлы»).

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
├── cases_tools_factory.py   # клиент сервиса кейсов по CASES_* + case_* и task_add, task_list, task_update, task_close
├── scheduler_tools_factory.py # клиент сервиса расписаний по SCHEDULER_API_* + schedule_add, schedule_list, schedule_cancel
├── todoist_tools_factory.py # Todoist как задачник: find_tasks, read_task, task_link; build_task_mirror — отражение задач
├── gmail_tools_factory.py   # search_mail, read_mail, draft_reply, draft_mail поверх GmailClient (OAuth refresh token)
├── whatsapp_tools_factory.py # коннектор WhatsApp по env (+ клиент WhatsApp Web по WHATSAPP_WEB_*) + search_whatsapp, read_whatsapp, list_whatsapp_chats
├── colleague_mail_tool_gateway.py # ColleagueMailToolGateway: вызов colleague_send → OutgoingMail → ColleagueMailSender
├── telegram_tools_factory.py # коннектор Telegram владельца по TELEGRAM_USER_SECRETS_FILE + search_telegram, read_telegram, list_telegram_chats
├── protocols/               # IWhatsAppSource, ITelegramSource — что бот берёт от коннекторов переписки (протоколы src.conversations)
└── file_tools_factory.py    # file_take (источники регистрацией), file_read, file_view, file_send поверх WorkFolder
workers/mcp/                 # Ядро MCP (python -m workers.mcp): FastMCP, Streamable HTTP, свои фабрики — см. «Ядро MCP»
workers/colleague_digest/    # Сводка почты коллег: build_colleague_digest (её же зовёт бот) и ручной запуск
workers/scheduled_run/       # Исполнитель расписаний: сборка потока scheduled-runs, свой AIApplication, набор инструментов прогона
src/
├── access/                  # OwnerUpdateGate + UpdateGateInstaller: вход только владельцу
├── agent_notifications/     # Уведомления рабочих агентов из RabbitMQ: журнал, пересылка владельцу, потребитель
├── scheduled_runs/          # Запуски по расписанию из RabbitMQ (schedule.due): разбор, журнал, исполнитель, потребитель — без модели и Telegram
├── colleague_mail/          # Почта ассистентов коллег (RabbitMQ): формат, журнал, справочник, отправка, приём, сводка — без модели
├── ai_tools/                # Инструменты модели: пакет на инструмент, класс — наследник BaseTool
├── chat/
│   ├── actions/
│   │   ├── send_to_agent_action.py   # Текст → AIApplication.process_message → ответ в чат
│   │   ├── system_prompt_builder.py  # data/system_prompt.txt: разделы подключённых коннекторов + дата на каждый запрос
│   │   ├── transcribe_voice_action.py
│   │   └── protocols/                # IConversationAI, ISystemPromptBuilder, ITranscriber, ...
│   ├── albums/                       # AlbumBuffer: фото альбома копятся до тишины, потом одним запросом
│   └── handlers/
│       ├── text_message_handler.py
│       ├── clear_command_handler.py  # /clear — AIApplication.clear_context(thread_id)
│       ├── voice_message_handler.py
│       ├── photo_message_handler.py, document_message_handler.py  # фото/PDF — вложениями, текстовые — текстом
│       ├── attachment_limits.py      # лимит Claude на картинку (5 МБ в base64)
│       ├── attachment_labels.py      # строки «[вложение: имя]» перед подписью владельца
│       └── protocols/                # IConversationClearer
├── cases/                   # CasesHttpClient — клиент сервиса кейсов assistant_cases (модели, ошибки, UntrustedCaseFrame)
├── scheduler/               # SchedulerHttpClient — клиент сервиса расписаний assistant_scheduler (модели, ошибки)
├── task_manager/            # Порт задачника: модели, ошибки, Protocol-ы (реализация — src/todoist), без реализаций
├── todoist/                 # TodoistHttpClient (API v1, close без reopen/delete; activities) и реализация порта: TodoistTask{Reader,Writer}, TodoistChangeFeed
├── task_mirror/             # Отражение задач self в задачник через порт: наружу — слушатель инструментов задач и перенос, внутрь — поток по журналу
├── conversations/           # Контракт источника переписки: модели, ошибки, Protocol-ы (реализации — gmail, whatsapp)
├── gmail/                   # GmailClient (поиск, чтение, вложения, черновики — без отправки), UntrustedMailFrame
├── whatsapp/                # Источник переписки WhatsApp: платформенные реализации протокола src.conversations
│   ├── macos_desktop/       # WhatsApp Desktop на macOS: чтение снимка ChatStorage.sqlite и медиа (host/ — хост-процесс снимка)
│   └── web_media/           # Клиент сервиса WhatsApp Web на хосте: документ, удалённый с CDN (платформенно-нейтральный)
├── telegram_user/           # Переписка Telegram владельца: MTProto (Telethon) от его аккаунта, только чтение
├── files/                   # Механика «файл»: WorkFolder, источники (IFileSource; mail/dropbox/chat), ридеры, растр, OverflowFolder, Sweeper
└── voice_recognition/       # HttpTranscriber, NativeTranscriber
scripts/
└── gmail_auth.py            # Получение refresh token Gmail владельца в pass (standalone, uv run)
data/
├── system_prompt.txt        # Системный промпт ассистента; {today}, {now}, {timezone} подставляются на каждый запрос
├── schedule_run_prompt.txt  # Раздел промпта прогона по расписанию — дописывается к системному промпту бота
├── phrases.json, roles.json, languages.json
deploy/                      # Образ и выкат в colima
```

## Движок: ai_framework

- Зависимость `ai-bot-framework[claude-sdk]` из git по тегу (`[tool.uv.sources]`). `claude-agent-sdk` везёт CLI
  Claude Code бинарём внутри колеса (`claude_agent_sdk/_bundled/claude`), Node не нужен
- Провайдер — `Provider.CLAUDE_SDK` в боте, чекапе и наполнении памяти; модель — `AI_MODEL`. Ключа API нет:
  CLI берёт `CLAUDE_CODE_OAUTH_TOKEN` из окружения, а нативно без него — локальный логин Claude Code.
  Ключ Claude API в окружении процесса держать нельзя: CLI предпочтёт его подписке, и счёт пойдёт по API
- Effort — `CLAUDE_CODE_EFFORT_LEVEL` (`low|medium|high|xhigh`), в проде `low` (умолчание в `up.sh` и `compose.yaml`,
  как у `AI_MODEL`). `ClaudeSdkProvider` effort/thinking не передаёт, но SDK отдаёт CLI окружение процесса целиком,
  а CLI читает переменную сам — поэтому env, а не код. При `low` CLI не включает thinking: замер 26.09.2026 на
  claude-sonnet-5 — ход −30 % времени, −39 % output-токенов к умолчанию CLI. Переменная контейнера действует на всё,
  что запущено в нём, — и на `workers.checkup`/`workers.memory_fill` через `docker exec`; отдельный `docker run` образа
  её не получит (compose-сервис один — `bot`). Нужен другой effort одному процессу — задать env этого процесса.
  Нативно переменной нет — действует умолчание CLI
- `ClaudeSdkProvider` (с v0.9.3) держит сессию CLI на тред; `clear_context` её сбрасывает. Сессии CLI — в `$HOME/.claude`
- Память диалога — `AI_DB_URL`: та же БД `personal_assistant`, схема `ai` (`options=-csearch_path%3Dai`).
  Миграции ai_framework применяются при входе в `with ai:`, но саму схему не создают: `CREATE SCHEMA IF NOT EXISTS ai` — один раз руками
- Тред диалога — `str(user_id)`, в истории последние `HISTORY_TURNS_LIMIT = 10` ходов
- Перед каждым запросом `SendToAgentAction` обновляет системный промпт (`update_system_prompt`) — в нём сегодняшняя дата
  в поясе `OWNER_TIMEZONE`
- `/clear` — `AIApplication.clear_context(thread_id)`: чистит историю треда владельца и (с v0.9.3) сбрасывает
  сессию SDK этого треда. `/context` нет: статистика была у сессии Claude Code
- Зависимость — `ai-bot-framework[claude-sdk,s3]` тега `v0.9.5` (v0.9.2 не брать). С v0.9.5 `Attachment` в результате
  инструмента (`execute` возвращает `list[str | Attachment]`) уходит модели image-контентом MCP — на этом стоит `file_view`
- Все хендлеры — только роль `admin` (второй слой после фильтра владельца, см. «Безопасность»)

## Ядро MCP

Второй composition root над тем же `src/`: инструменты из `src/ai_tools` по сети как удалённый MCP-сервер для
агентских приложений (Claude, ChatGPT). Модели и диалога в ядре нет. Бот не затронут: `workers.mcp` не
импортирует `workers.bot` и наоборот (контракт independence в import-linter), фабрики у ядра свои.

- Запуск: `uv run python -m workers.mcp`. FastMCP 4.x, транспорт Streamable HTTP, путь `/mcp`,
  адрес `MCP_HOST:MCP_PORT` (умолчание `127.0.0.1:8790`; в контейнере — `0.0.0.0`)
- Набор — ровно пять: `find_tasks`, `read_task` (порт задачника, реализация `TodoistTaskReader`),
  `dropbox_tree`, `dropbox_search`, `dropbox_read` (через `DropboxBoundary`) — `core_tools_factory.py`
- `BaseToolAdapter` (`base_tool_adapter.py`) — FastMCP `Tool` над `BaseTool`: имя, description и input_schema
  из `BaseTool` (`parameters` можно подменить), `Input(**args)`, `execute` с пустым `ToolContext` в потоке.
  Результат — как `_to_mcp_content` ai_framework (`tool_output_content.py`). Ошибка `execute` и неверные
  аргументы — результат с `isError` и текстом, а не протокольная ошибка: модель видит, что поправить
- Доступ волны 0 — статический ключ: `Authorization: Bearer <MCP_STATIC_KEY>`, сверка `hmac.compare_digest`
  (`StaticKeyVerifier` — `TokenVerifier` FastMCP); без ключа или с чужим — 401
- Сборка — `build_core_server(tools, auth, middleware=())` и `build_core_app(server)`
  (`core_server_factory.py`): middleware FastMCP передаются списком; набор ядра —
  `build_core_middleware(journal, allowed_projects)`: снаружи журнал, внутри проект (порядок важен — журнал
  видит отказ проекта)
- Проект (`project/`): заголовок `X-Project` сильнее всего и не сверяется (его шлёт настроенный нами клиент);
  иначе параметр `project`, который `with_project_parameter` добавляет в input_schema каждого инструмента, а
  адаптер снимает перед `Input(**args)`. `project` вне `MCP_ALLOWED_PROJECTS` — `ProjectGate` отвечает
  `isError` «Проект не разрешён», инструмент не зовётся. Нет ни того, ни другого — вызов идёт, проект пуст.
  Итог (`ProjectResolution`: project, source header|param|none, allowed) лежит в request-state FastMCP
  под `PROJECT_RESOLUTION_STATE_KEY` — оттуда его берёт журнал. До инструментов проект пока не доходит
- Журнал (`journal/`): `RequestJournal` (`on_message`) пишет JSON-строку на каждый входящий запрос, включая
  notifications и запросы, упавшие исключением (try/finally). Поля: `time` (UTC), `method`, `client`
  (clientInfo: из initialize, дальше — из `client_params` сессии), `headers`, `meta` (wire `_meta` запроса),
  `tool`, `project`, `project_source` (null вне tools/call), `outcome` ok|error|denied. Заголовки с `auth`,
  `cookie`, `token`, `secret`, `api-key`, `apikey`, `password` в имени — значением `***`. Запись —
  `JsonLinesFile`: append с закрытием файла на каждую строку, без ротации
- Env: `TODOIST_TOKEN`, `DROPBOX_ROOT`, `MCP_STATIC_KEY`, `MCP_JOURNAL_FILE` (путь к файлу журнала, каталог
  создаётся при старте) обязательны — без любого ядро не стартует; `MCP_ALLOWED_PROJECTS` (через запятую,
  пусто — любой `project` параметром отклоняется), `MCP_HOST`, `MCP_PORT`, `LOG_LEVEL` необязательны
- Тест — `tests/mcp/`: ядро на подменах, клиент mcp SDK по Streamable HTTP (`running_core`); журнал и
  проект — `test_request_journal.py`
- Прод (Mac mini): сервис `mcp` в `deploy/compose.yaml`, контейнер `personal_assistant_mcp` из того же образа
  `personal_assistant-bot:latest`, `command: python -m workers.mcp`, выкат вместе с ботом через `deploy/up.sh`.
  Порт — только `127.0.0.1:8790` хоста (`MCP_HOST=0.0.0.0` внутри контейнера). Dropbox — тот же `~/Dropbox`, но
  `/dropbox:ro`, с теми же оверлеями закрытых папок (при `:ro` docker не создаёт точку монтирования — папка оверлея
  обязана существовать в `~/Dropbox`, иначе контейнер не стартует). Журнал — том `~/docker/personal_assistant/mcp` → `/mcp`,
  `MCP_JOURNAL_FILE=/mcp/requests.jsonl`. `MCP_ALLOWED_PROJECTS` — env compose (умолчание `assistant`).
  Ключ — pass `assistant/personal_assistant/mcp-key` (первая строка); нет записи — `up.sh` заводит её сам
  (`openssl rand -hex 32`). Проверка: `docker ps --filter name=personal_assistant_mcp`,
  `docker logs --tail 20 personal_assistant_mcp` (строки `MCP tools:` и `MCP journal:`),
  `tail ~/docker/personal_assistant/mcp/requests.jsonl`
- Подключение Claude Code — `.mcp.json` в папке проекта. Ключ не пишется в файл: его печатает `headersHelper`
  (shell-команда, stdout — JSON-объект заголовков, перекрывает одноимённые `headers`; запускается на каждое
  подключение, таймаут 10 с, у проектного `.mcp.json` — только после принятия доверия папке). `X-Project` —
  статическим заголовком:

  ```json
  {
    "mcpServers": {
      "assistant-core": {
        "type": "http",
        "url": "http://127.0.0.1:8790/mcp",
        "headers": {"X-Project": "assistant"},
        "headersHelper": "printf '{\"Authorization\": \"Bearer %s\"}' \"$(GNUPGHOME=$HOME/docker/personal_assistant/gnupg pass show assistant/personal_assistant/mcp-key | head -n 1)\""
      }
    }
  }
  ```

  `GNUPGHOME` — связка ассистента (без пина, работает и из `claude -p`). Сервер из проектного `.mcp.json` Claude
  Code включает после одобрения (`enabledMcpjsonServers` в `.claude/settings.local.json`), инструменты —
  `mcp__assistant-core__*`

## Инструменты (tools)

Точка регистрации одна — список `tools` в `workers/bot/__main__.py`, он передаётся в `AIApplication`.
`ClaudeSdkProvider` отдаёт их CLI как SDK MCP-сервер `ai-framework-tools`: модель видит `mcp__ai-framework-tools__<name>`.
До v0.9.4 ai_framework дописывал в системный промпт список инструментов голыми именами — модель порой вызывала
голое `wiki_create_page`, CLI отвечал «No such tool available», и бот говорил владельцу, что инструменты недоступны.
С v0.9.4 блок «Available tools» при `ClaudeSdkProvider` идёт с полными именами. `data/checkup_prompt.txt` и
`data/memory_fill_prompt.txt` называют инструменты полными именами; `data/system_prompt.txt` — короткими, а в начале
раздела «Возможности» указание вызывать по полному имени `mcp__ai-framework-tools__<имя>`: оно остаётся до
подтверждения на проде, при правке промпта его не терять. `claude_sdk_live_check bot|cases` идёт с настоящим
`data/system_prompt.txt` (собранным `SystemPromptBuilder`), `checkup` — с коротким промптом-заглушкой.

### Разделы промпта по коннекторам

Раздел коннектора в `data/system_prompt.txt` обрамлён строками `<!-- connector:<ключ> -->` и
`<!-- /connector:<ключ> -->` (ключи `tasks`, `gmail`, `whatsapp`, `telegram`, `scheduler`; обрамлять можно и отдельные строки внутри
чужого раздела — так сделаны строки «Файлов» про почту и WhatsApp). `SystemPromptBuilder(connectors=…)` один раз
на старте оставляет тело разделов зарегистрированных коннекторов и вырезает остальные вместе с маркерами; серии
пустых строк схлопываются. Список собирает `__main__.py` по построенным клиентам (`tasks` — задачник, сейчас клиент Todoist; `mail`, `whatsapp`, `telegram`, `scheduler` — клиент сервиса расписаний)
и пишет в лог строкой `Prompt connectors: …`. Упоминание инструмента коннектора вне его маркеров — ошибка:
без коннектора модель увидит инструмент, которого нет (тест `tests/chat/test_system_prompt_builder.py`).
Раздел «Кейсы» от коннекторов не зависит.

### Встроенные инструменты CLI выключены

`deploy/claude-code/managed-settings.json` кладётся в образ как `/etc/claude-code/managed-settings.json`
(root, uid 1000 его не перепишет). Managed settings грузятся всегда, независимо от `setting_sources`:

- `permissions.allow` — `mcp__ai-framework-tools` (весь сервер). Без него инструменты бота не вызываются: при
  `allowManagedPermissionRulesOnly` правило `allowed_tools` от ai_framework (флаг CLI) не действует, `permission_mode`
  default просит разрешения, дать его в SDK некому — модель отвечает владельцу «нужно ваше разрешение»
- `permissions.deny` — все встроенные инструменты CLI поимённо: запрещённый инструмент убирается из контекста модели
- `env.ENABLE_TOOL_SEARCH=false` — MCP-инструменты всегда в контексте целиком: `ToolSearch` в deny, и отложенный
  за ним инструмент модель не нашла бы
- `PreToolUse`-хук на всё — страховка на инструмент, которого нет в списке (новая версия CLI): пропускает только
  `mcp__ai-framework-tools__*`, остальное блокирует
- `allowedMcpServers` — только `ai-framework-tools`; `allowManaged{PermissionRules,Hooks}Only` — правила и хуки
  пользователя и проекта не действуют. `ENABLE_CLAUDEAI_MCP_SERVERS=false` в образе — без коннекторов claude.ai

Нативно `/etc/claude-code` (на macOS `/Library/Application Support/ClaudeCode`) — это собственный Claude Code
владельца, поэтому проверочные скрипты подключают тот же файл как project settings временного каталога:

- `uv run python -m scripts.claude_cli_tools_check` — список инструментов из init CLI, без вызова модели;
  в образе: `docker run --rm -v "$PWD/scripts:/app/scripts:ro" --entrypoint python personal_assistant-bot:latest -m scripts.claude_cli_tools_check`.
  Должно быть ровно `mcp__ai-framework-tools__…`
- `uv run python -m scripts.claude_sdk_live_check bot|cases|scheduler|checkup` — живой прогон `AIApplication(CLAUDE_SDK)` со
  списком инструментов бота или чекапа на локальных подменах источников (задачник — `LiveTaskManager` поверх
  `FakeTodoistClient`: задачи, заведённые владельцем прямо в задачнике, и повторяющаяся; сервис кейсов —
  `InMemoryCasesService` на `httpx.MockTransport` под настоящим `CasesHttpClient`; сервис расписаний —
  `InMemorySchedulerService` так же под настоящим `SchedulerHttpClient`, ближайших у cron не считает; в конце прогона в лог идут
  вызовы сервиса кейсов, записанные события, задачи задачника, перенесённые и закрытые в нём), вызовы модели
  настоящие. `bot` — с отражением и переносом, как в проде (реплики «перенеси … на пятницу», «… сделал»);
  `cases` — только инструменты кейсов и задач и промпт без коннекторов, как бот без `TODOIST_TOKEN`;
  `scheduler` — инструменты кейсов и расписаний с разделом «Расписания» (реплики «в пятницу в 10 проверь, ответил ли
  нотариус», первый понедельник месяца, список, отмена; они же в конце `bot`)
  Нативно файл — project settings, а `allowManaged*Only` действует только из managed: запрос разрешения на
  инструмент бота ловится лишь прогоном в образе — `docker build -f deploy/Dockerfile -t <свой тег> .`, затем
  `docker run --rm -e CLAUDE_CODE_OAUTH_TOKEN -v "$PWD/scripts:/app/scripts:ro" -v "$PWD/tests:/app/tests:ro" -v "$PWD/deploy:/app/deploy:ro" --entrypoint python <тег> -m scripts.claude_sdk_live_check bot`

Обновил `claude-agent-sdk` в `uv.lock` — прогони `claude_cli_tools_check`: новый инструмент CLI добавляется в `deny`.
Инструменты вызываются синхронно изнутри event loop провайдера: `asyncio.run` в их коде падает (так `GitCli`
гоняет git своим циклом в отдельном потоке)

### Todoist и Gmail

Регистрируются в `__main__.py` через `workers/bot/todoist_tools_factory.py` и `workers/bot/gmail_tools_factory.py`,
если заданы переменные: `TODOIST_TOKEN` — задачник владельца: `find_tasks`, `read_task`, с `CASES_*` ещё
`task_link` (инструменты — на порту `src.task_manager`, Todoist подставляет фабрика); все три `GMAIL_*` — `search_mail`, `read_mail`,
`draft_reply`, `draft_mail` (задана только часть `GMAIL_*` — бот падает на старте). В проде compose требует все четыре.
Список зарегистрированных инструментов пишется в лог на старте строкой `AI tools: …`.

Граница задаётся набором методов, а не промптом:

- **Почта не отправляется.** Инструмента отправки нет, в `GmailClient` нет метода send. `draft_reply` — ответ в
  существующий тред, адресата и тему берёт код из исходного письма; `draft_mail` — черновик нового письма, адресата
  и тему задаёт модель (отправляет владелец из Gmail). Оба принимают `file_ids` — вложения из рабочей папки.
  Scope токена — `gmail.readonly` + `gmail.compose`
- `read_mail` перечисляет вложения с `attachment_id` — это partId части письма (короткий и стабильный), а не
  attachmentId Gmail: `GmailClient.get_attachment` находит часть по partId и качает по свежему attachmentId
- **Задачник — порт, Todoist — его реализация** (решение владельца 29.09.2026). Контракт — `src/task_manager/` по
  образцу `src/conversations`: модели (`ManagedTask` с ref «<задачник>:<id>», `TaskSearch`, `TaskManagerChange`,
  `TaskManagerIdentity`), ошибки (`TaskManagerError`, `ForeignTaskRefError`), узкие Protocol-ы (`ITaskSearch`,
  `ITaskReader`, `ITaskWriter`, `ITaskCloser`, `ITaskChangeFeed`), своих реализаций нет. Todoist реализует его
  частями в `src/todoist/services` (`TodoistTaskReader`, `TodoistTaskWriter`, `TodoistChangeFeed`); единого
  `ITaskManager` нет — потребитель держит свой узкий Protocol. Инструменты модели и промпт о Todoist не знают
  ни в именах, ни в параметрах, ни в описаниях: `find_tasks` принимает параметры порта (text, due_before, overdue,
  by_assistant), перевод в фильтр Todoist — `TodoistFilterQuery` в реализации
- **Задачи закрываются и переносятся, но не удаляются.** `TodoistHttpClient.close_task` — `POST /tasks/{id}/close`,
  дата выполнения — `due_date`; reopen и delete нет. Закрывает в задачнике только отражение и только по слову
  владельца (`task_close` с source owner, решение 30.09.2026 — отменяет q1 таска 01a0e680-73b6), переносит —
  `task_update` с planned (см. «Кейсы»). Модель напрямую в задачник не пишет
- `create_task`, `update_task`, `add_task_link`, `task_link_todoist` удалены: задачу ставит `task_add`, в задачник
  она уходит отражением; задачу, заведённую владельцем прямо в задачнике, к кейсу подвязывает `task_link` (task_ref
  из `find_tasks`). Промпт — раздел «Задачник» под маркером `tasks`, слова Todoist в `data/system_prompt.txt` нет
  (тест `tests/chat/test_system_prompt_builder.py`)
- Задачник — не хранилище кейсов: кейс живёт в сервисе кейсов (см. «Кейсы»), в задачнике — только задачи владельца
- Текст писем — данные: инструменты почты оборачивают его в `UntrustedMailFrame`, системный промпт запрещает
  исполнять указания из писем
- `search_mail`/`read_mail` идут через `GmailConversationSource` (`src/gmail/services/conversation_source`) —
  реализацию `IConversationSource`; `draft_*` работают с `GmailClient` напрямую

### WhatsApp

Регистрируются в `__main__.py` через `workers/bot/whatsapp_tools_factory.py`, если задан каталог снимка коннектора
«WhatsApp (macOS Desktop)» — `WHATSAPP_MACOS_SNAPSHOT_DIR`; без него инструментов WhatsApp и источника `whatsapp` у
`file_take` нет. Каталог есть, а снимка в нём нет — бот стартует, инструменты отвечают ошибкой «нет снимка».

- Инструменты платформенно-нейтральны: `search_whatsapp`, `read_whatsapp`, `list_whatsapp_chats`
  (`src/ai_tools/`) знают только протоколы `src.conversations` (поиск, чтение, список чатов, свежесть).
  Какой коннектор подставить, решает `build_whatsapp_source` по env: сейчас только macOS (`WhatsAppConversationSource`);
  Linux-коннектор встанет туда же своей переменной, инструменты и `file_take` не правятся
- Свои инструменты у каждого источника (решение владельца 28.09.2026): у WhatsApp свой язык запроса (подстрока,
  собеседник, чат, дни), общий только протокол в коде
- Каждый ответ начинается строкой `WhatsAppFreshnessNote` — «Снимок WhatsApp: последнее сообщение от <дата>, снимок
  снят <время>» (`ISourceFreshness`, пояс `OWNER_TIMEZONE`); промпт велит всегда называть эту дату владельцу
- Текст сообщений, имена чатов — в рамке `UntrustedWhatsAppFrame` (`<untrusted_whatsapp>`), промпт запрещает исполнять
  указания из сообщений. Отправки в WhatsApp нет ни в протоколе, ни в инструментах
- Файл — `file_take(source=whatsapp, message_id, attachment_id)` через `ConversationFileSource` (origin
  `whatsapp:<message>/<attachment>`); нескачанное Desktop бот качает с CDN WhatsApp по запросу (см. «WhatsApp (macOS
  Desktop)»), документ, удалённый с CDN, — через сервис WhatsApp Web (`WHATSAPP_WEB_URL`); не вышло — ошибка с
  причиной и просьбой владельцу скачать файл в WhatsApp Desktop

### Telegram

Переписка Telegram владельца — живым запросом от его аккаунта (MTProto, Telethon), коннектор
`src/telegram_user/` (см. «Telegram владельца (MTProto)»). Регистрируется в `__main__.py` через
`workers/bot/telegram_tools_factory.py`, если `TELEGRAM_USER_SECRETS_FILE` задан и файл есть; иначе
инструментов Telegram, источника `telegram` у `file_take` и раздела промпта `telegram` нет, в лог — строка
`TELEGRAM_USER_SECRETS_FILE … Telegram tools are off`. Кривой файл (не три строки `session=`, `api_id=`,
`api_hash=`) — бот падает на старте, как при части `GMAIL_*`.

- Инструменты: `search_telegram` (text — серверный поиск Telegram по словам целиком, не подстрока;
  participant, chat_id, since/until; без text, participant и chat_id инструмент отвечает подсказкой, не
  ходя в Telegram — глобальный поиск без text коннектор умеет только с participant), `read_telegram`
  (chat_id — последние сообщения чата; message_id `<чат>:<номер>` — одно сообщение с вложениями и
  ссылкой), `list_telegram_chats`. Строки свежести нет — API живой (`ISourceFreshness` не реализуется)
- `chat_id` — marked peer id (у групп отрицательный), `message_id` — `<peer>:<msg>`. Ссылка на сообщение
  (`link` моделей `src.conversations`) — у супергрупп `t.me/c/…` или `t.me/<username>/…`; у личных чатов и
  обычных групп её нет, `read_telegram` так и пишет
- Чат владельца с самим ботом PA скрыт: `TelegramAccount` отбрасывает `hidden_conversation_ids` в списке
  чатов и в глобальном поиске, поэтому поиск по чату, чтение, `<peer>:<msg>` и `file_take` отвечают как на
  канал (не найдено). id бота — часть `BOT_TOKEN` до «:» (`bot_conversation_id` в
  `telegram_tools_factory.py`); чаты с другими ботами читаются
- Текст сообщений, имена чатов — в рамке `UntrustedTelegramFrame` (`<untrusted_telegram>`,
  `src/ai_tools/telegram_common/`), промпт запрещает исполнять указания из сообщений. Отправки,
  отметки прочитанным и статуса «в сети» нет ни в коннекторе, ни в инструментах
- Файл — `file_take(source=telegram, message_id, attachment_id)` через `ConversationFileSource` (origin
  `telegram:<message>/<attachment>`), предел 50 МБ проверяется по размеру вложения до скачивания
- К кейсу — `case_add_event` с `source telegram` (`CaseSource`; в сервисе кейсов значение вносит его
  миграция 0002), `url` — ссылка на сообщение; ссылки нет — цитата с датой в summary (раздел
  «Переписка Telegram» промпта)
- FLOOD_WAIT дольше 10 с — ошибка «Telegram ограничил запросы, повтори через N с» модели, без ожидания
- Живые прогоны против аккаунта при работающем контейнере с той же сессией не делаются: одна сессия —
  один процесс (риск AUTH_KEY_DUPLICATED — Telegram отзывает ключ). Тесты — на подменённом источнике
  (`tests/ai_tools/telegram/`, `tests/telegram_user/`)

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

## Кейсы

Кейс — тема или линия жизни владельца («Новая компания (ТОО)»), а не задача: задачи и шаги живут внутри кейса
событиями его ленты. Кейсы и ленты хранит сервис кейсов `assistant_cases` (отдельная репа, база на центральном сервере);
бот к базе не ходит — только по HTTP API сервиса. Пользователь записи определяется ключом API (`CASES_API_KEY`),
поля пользователя в запросах нет; чужой кейс отвечает 404, как несуществующий.

- Клиент — `src/cases/repos/cases_http_client.py` (`CasesHttpClient`, httpx, заголовок `X-API-Key`): все ручки
  контракта — `/cases` (завести, изменить, найти, прочитать с лентой), `/cases/{id}/events` (201 — записано, 200 —
  такое событие уже есть: `EventAddition.created`), `/tasks` (выборка, PATCH, `close`, `reopen`). PATCH шлёт только
  заданные поля (`exclude_unset`), остальные запросы — без пустых
- Ошибки — `src/cases/errors/`, общий предок `CasesServiceError`: 404 `case_not_found`/`task_not_found` →
  `CaseNotFoundError`/`TaskNotFoundError`, 401 → `CasesUnauthorizedError`, 409 → `ExternalIdTakenError`,
  422 → `CasesValidationError`, прочее ≥ 400 → `CasesServiceFailureError`, сеть/таймаут →
  `CasesServiceUnavailableError`. Инструменты ловят `CasesServiceError` и отвечают модели `{"error": …}` —
  сервис лёг, бот работает
- Инструменты кейса (`src/ai_tools/case_*`): `case_find` (q, status), `case_open` (title, summary — что за тема
  и зачем), `case_read` (case_id, events_limit — лента по `occurred_at` строками «ДД.ММ.ГГГГ ЧЧ:ММ · источник ·
  пересказ · ссылка» в поясе `OWNER_TIMEZONE`, у задач — id, статус, срок, исполнитель), `case_add_event` (kind
  note|message|file|link — задачи не им; `occurred_at` без пояса — пояс владельца, не передан — сейчас),
  `case_update` (title, summary, status). Имена инструментов и параметров — опора промпта, не переименовывать
- Инструменты задач (`src/ai_tools/task_*`): задача — событие ленты `kind task` с четырьмя полями (статус, срок,
  исполнитель, внешний id). `task_add` (case_id, summary — что сделать и зачем, assignee, due, occurred_at, source
  owner|assistant) → `POST /cases/{id}/events`; без `case_id` — в служебный кейс «Без темы» по адресу
  `/cases/inbox/events`. `task_list` (assignee, status — умолчание open, due_before, case_id) — строки
  «id · срок · исполнитель · кейс · текст» по сроку, без срока в конце, в рамке `UntrustedCaseFrame`. `task_update`
  (task_id, planned, due, assignee, summary — причина, source) → `PATCH /tasks/{id}`, только заданные поля;
  `task_close` (task_id, done|cancelled, summary, source owner|assistant) → `POST /tasks/{id}/close`. Срок (`due`) —
  жёсткая граница (дедлайн), не «когда займусь»; модель трогает его, только если владелец сказал «дедлайн»
- **Перенос** — `task_update` с `planned`: дата выполнения («перенеси на пятницу», решение владельца 30.09.2026) — у
  нас не хранится, уходит в задачник (`due_date`), в ленту кейса — событие `note` ««<задача>» — дата выполнения в
  <задачник>: ДД.ММ.ГГГГ. <причина>» (`PATCH /tasks/{id}` при одном planned событий не пишет). Делает
  `TaskRescheduler` (`src/task_mirror/services/task_rescheduling`, сборка — `build_task_rescheduler` в
  `__main__.py`), инструмент видит его как `ITaskPlanner`. Отказы — наследники `TaskManagerError` из
  `src/task_mirror/errors`: задача не self, без external_id или чужого задачника; закрыта; повторяющаяся
  («перенос сломает повтор», без записи в задачник). Задачника нет — planned отвечает ошибкой без запросов,
  промпт велит записать перенос заметкой в ленту кейса
- **Закрытие** уходит в задачник только при `source owner` (q2 таска 01a0eb76-6d5e): done и cancelled — оба
  закрытие, удаления нет. При `source assistant` задача в задачнике остаётся открытой — `task_close` так и
  дописывает модели, промпт велит сказать владельцу
- Исполнитель — `self | assistant | agent:<имя> | person:<имя> | colleague:<user>`
  (`src/ai_tools/task_add/task_assignee.py`); другое — ошибка модели без запроса к сервису. Исполнитель только
  записывается: поручений агентам и отправки коллегам нет
- Точка расширения «задача записана / изменена / закрыта» — Protocol-ы у инструментов (`ITaskRecordedListener`,
  `ITaskChangedListener`, `ITaskClosedListener` в `protocols/` своих пакетов), слушатель вызывается только после
  успешного ответа сервиса. Подставляет их `build_cases_tools` (`task_recorded`, `task_changed`, `task_closed`);
  не передан — ничего. `task_closed(task, closure)` получает и `TaskClosure` — слушатель знает, кто закрыл.
  Задачник инструменты задач не знают: отражение цепляется слушателем, перенос — `ITaskPlanner`
- **Отражение в задачник** (`src/task_mirror` поверх порта `src.task_manager`, при `TODOIST_TOKEN` и `CASES_*`;
  сборка — `build_task_mirror`, Todoist подставляет только composition root). Отражаются только задачи с
  исполнителем `self`, связь — `external_id` = ref задачника (`todoist:<id>`, данные не мигрировали):
  - наружу — `TaskMirrorListener` на `task_recorded`/`task_changed`/`task_closed`: новая задача self → `add_task`
    порта (в Todoist — метка `pa`, текст — summary, срок → `deadline_date`), её ref → `PATCH /tasks/{id}` external_id;
    смена срока → дедлайн; исполнитель сменился на self — задача уходит в задачник; закрытие с source owner →
    `close_task`. Смена исполнителя с self в задачник не уходит. Сбой задачника/сервиса — строка в лог, ответ
    модели не ломается
  - внутрь — поток `todoist-mirror` (`start_todoist_mirror`, раз в 10 мин, `MirrorPass`): сначала отражает
    открытые задачи self без `external_id` (догоняет сбойные), затем `GET /activities` (`item:completed|uncompleted|
    updated|deleted` с прошлого прохода минус 2 мин, первый проход — за сутки) и по каждой нашей задаче self:
    completed → close done, deleted → close cancelled, uncompleted → reopen (`source todoist` — ключ задачника,
    `source_ref` `todoist:activity:<id>`), смена дедлайна (`extra_data.deadline`) → PATCH due. Разбор журнала —
    `TodoistChangeFeed` (изменения порта `TaskManagerChange`). Повтор события не даёт — сверка со статусом и срок,
    плюс уникальность source_ref в сервисе; эхо своего закрытия (item:completed) и переноса (смена due_date)
    второго события не пишет. Сбой прохода — строка в лог, следующий через 10 мин
  - задача, заведённая владельцем прямо в задачнике, сама не приходит; поднял тему, просит перенести или закрыть —
    модель находит её `find_tasks` и подвязывает `task_link` (task_ref, case_id — не уверен, без него, в «Без
    темы», summary; `TaskAdoption`): задача self с её external_id, дальше переносится, закрывается и отражается.
    Уже подвязанная второй раз не записывается
  - границы — import-linter: «task manager contract stands alone» (`src.task_manager` не знает соседей), «todoist
    depends only on task manager contract», «task mirror bridges only cases and task_manager» (`src.task_mirror`
    не импортирует `src.todoist`), «ai tools know task manager port, not todoist or task mirror»; `src.cases` не
    знает задачника. Мост кейсов и задачника — только `src.task_mirror`
- Пересказы в ленте пишутся по чужим письмам и сообщениям: `case_find` и `case_read` отдают их в рамке
  `UntrustedCaseFrame` (`<untrusted_case>`)
- Поведение задаёт раздел «Кейсы» `data/system_prompt.txt`: сперва `case_find` по теме, неясна тема — вопрос
  «для чего это?», новый кейс — только под новую тему; задача — `task_add` в кейсе с исполнителем (self по
  умолчанию) и «что и зачем» в summary; «перенеси на …» — `task_update` planned, дедлайн — только по слову
  «дедлайн»; «сделал» — `task_close` source owner; задачу задачника без кейса — сперва `task_link`, повторяющуюся
  не переносить; к кейсу пишется событие (`source_ref`), а не собеседник, одно событие —
  один кейс, не уверен — вопрос с кандидатами и до ответа не писать; вопрос о кейсе — `case_read`, в источник —
  только за подробностями
- Регистрация — `workers/bot/cases_tools_factory.py` при `CASES_API_URL` и `CASES_API_KEY`; задана одна из двух —
  бот падает на старте (как `GMAIL_*`). От `TODOIST_TOKEN` не зависит
- Граница — import-linter «cases client stands alone»: `src.cases` не импортирует соседей; инструменты берут у него
  модели и ошибки, Protocol-ы — свои, в `src/ai_tools/case_*/protocols/`

## Вики

Слой `src/wiki` — локальная git-копия `obsidian_wiki` (`WIKI_DIR`): первый вызов делает clone по `WIKI_REMOTE_URL`
на пустом каталоге, дальше pull перед чтением; запись — коммит `pa: …` и push в `main` ключом `WIKI_SSH_KEY_PATH`.
Сборка — `build_wiki_tools` в `workers/bot/__main__.py`: один `WikiFactory` на бот, инструменты
`wiki_search` (`WikiSearcher` поверх `WikiReader`), `wiki_read`, `wiki_create_page`, `wiki_append`.
Без `WIKI_DIR` инструментов `wiki_*` нет.

Память (`memory_*`) — за протоколом `IWikiStorage` (`src/memory/repos/protocols/`), реализация выбирается
`MEMORY_STORAGE` одинаково в боте, `workers.memory_fill` и `workers.checkup`: не задана или `local` —
`LocalFolderStorage`, файлы в `MEMORY_DIR` (дефолт `~/.local/share/personal_assistant/memory`), без git и сети;
`wiki` — `WikiPageStorage` поверх вики (бот — через тот же `WikiFactory`, что `wiki_*`, общий замок на копию;
требует `WIKI_DIR`). На проде владельца `MEMORY_STORAGE: wiki` задан в `deploy/compose.yaml`.
В системном промпте: факт из вики — со ссылкой на путь страницы; служебные страницы памяти — только через `memory_*`.

## Безопасность: бот слышит только владельца

- `src/access`: `OwnerUpdateGate` пропускает только `message` из личного чата и `callback_query` с сообщением
  в личном чате, отправитель и чат — `OWNER_TELEGRAM_ID`. `UpdateGateInstaller` ставит его в
  `TeleBot.process_new_updates` (`app.core.bot`) — раньше `EnsureUserMiddleware`, next-step и любых хендлеров:
  посторонний не получает ответа и не попадает в `users`. Отброшенный апдейт — строка в лог
  `Dropped update: type=… from=… chat=…`, без содержимого; offset `getUpdates` за ним сдвигается
- `OWNER_TELEGRAM_ID` не задан или не число — `main()` падает до `BotApplication` и поллинга
- `/request_role` в `__main__.py` не регистрируется (bot_framework регистрирует свой, но до него доходит только
  владелец). Проверки роли `admin` в хендлерах — второй слой
- Прод: значение — pass `assistant/personal_assistant/owner-telegram-id`

## Переменные окружения (.env)

```
BOT_TOKEN=токен-бота
OWNER_TELEGRAM_ID=123456789                    # Telegram ID владельца; бот слышит только его в личном чате
BOT_DB_URL=postgres://user:password@localhost:5432/personal_assistant?sslmode=disable
REDIS_URL=redis://localhost:6379/4
AI_DB_URL=postgres://user:password@localhost:5432/personal_assistant?sslmode=disable&options=-csearch_path%3Dai
CLAUDE_CODE_OAUTH_TOKEN=токен подписки          # claude setup-token; нативно необязательная — CLI возьмёт локальный логин
AI_MODEL=claude-sonnet-5
CLAUDE_CODE_EFFORT_LEVEL=low                    # необязательная; effort CLI (low|medium|high|xhigh), прод — low; без неё — умолчание CLI
OWNER_TIMEZONE=Asia/Almaty                      # необязательная (дефолт Asia/Almaty); пояс для даты в системном промпте
VOICE_RECOGNITION_URL=http://localhost:8000     # необязательная (есть дефолт); HTTP-сервис распознавания речи (faster-whisper, GPU)
VOICE_RECOGNITION_API_KEY=ключ                  # заголовок X-API-Key для сервиса распознавания; без него сервис отвечает 401
VOICE_RECOGNITION_MODE=http                     # необязательная (дефолт http); http | native
WHISPER_MODEL=small                             # необязательная (дефолт small); модель для native-режима
LOG_LEVEL=INFO                                  # необязательная (дефолт INFO); логгеры TeleBot/urllib3/requests/httpx/anthropic всегда не ниже WARNING; DEBUG у ai_framework пишет вызовы инструментов
MEMORY_STORAGE=local                            # необязательная (дефолт local); local — память файлами в MEMORY_DIR, wiki — в вики (нужен WIKI_DIR)
MEMORY_DIR=~/.local/share/personal_assistant/memory  # необязательная (это дефолт); папка памяти в режиме local
WIKI_DIR=/path/to/obsidian_wiki                 # необязательная; локальная копия вики, пустой каталог — бот сам сделает clone; без неё нет wiki_*
WIKI_REMOTE_URL=git@github.com:sumarokov-vp/obsidian_wiki.git
WIKI_SSH_KEY_PATH=/path/to/deploy_key           # необязательная; без неё git берёт ssh-ключи/агент пользователя
DROPBOX_ROOT=/path/to/Dropbox                   # необязательная; без неё инструменты Dropbox не регистрируются
ATTACHMENTS_S3_ENDPOINT=https://fra1.digitaloceanspaces.com   # хранилище вложений (фото, PDF) — DO Spaces
ATTACHMENTS_S3_BUCKET=sumarokov-pa-attachments
ATTACHMENTS_S3_REGION=fra1
ATTACHMENTS_S3_ACCESS_KEY=ключ Spaces
ATTACHMENTS_S3_SECRET_KEY=секрет Spaces
CASES_API_URL=http://localhost:8000             # CASES_* — обе или ни одной; сервис кейсов assistant_cases, без них инструментов кейсов нет
CASES_API_KEY=ключ                              # X-API-Key сервиса кейсов; ключ определяет пользователя
TODOIST_TOKEN=токен                             # необязательная; задачник владельца (Todoist); без неё нет find_tasks/read_task/task_link и отражения
GMAIL_CLIENT_ID=id OAuth-клиента                # GMAIL_* — все три или ни одной; без них инструменты почты не регистрируются
GMAIL_CLIENT_SECRET=секрет OAuth-клиента
GMAIL_REFRESH_TOKEN=refresh token владельца     # uv run scripts/gmail_auth.py
RABBITMQ_URL=amqp://pa-consumer:пароль@localhost:5672/assistant   # необязательная; без неё уведомления агентов не принимаются
ASSISTANT_MAIL_URL=amqp://assistant-sumarokov:пароль@localhost:5672/assistants.sumarokov  # почта ассистентов; логин обязан быть assistant-<ASSISTANT_KEY>
ASSISTANT_KEY=sumarokov                         # ключ этого ассистента: адрес (ящик inbox.<ключ>) и поле from; с ASSISTANT_MAIL_URL — обе или ни одной
ASSISTANT_DIRECTORY_FILE=/path/to/directory.yaml  # необязательная; справочник коллег (ключ → имя, editor)
COLLEAGUE_DIGEST_AT=09:00                       # необязательная (дефолт 09:00, пояс OWNER_TIMEZONE); время суточной сводки почты коллег
WHATSAPP_MACOS_SNAPSHOT_DIR=~/docker/personal_assistant/whatsapp  # необязательная; снимок WhatsApp Desktop (macOS); без неё инструментов WhatsApp нет
WHATSAPP_WEB_URL=http://host.docker.internal:18790  # необязательная; сервис WhatsApp Web на Mac mini — запасной путь для документов, удалённых с CDN
WHATSAPP_WEB_TOKEN=                                 # ключ сервиса WhatsApp Web (Authorization: Bearer)
TELEGRAM_USER_SECRETS_FILE=/path/to/telegram_user  # необязательная; файл session=/api_id=/api_hash= Telegram владельца; нет файла — нет инструментов Telegram
SCHEDULER_API_URL=http://localhost:8000         # SCHEDULER_API_* — обе или ни одной; сервис расписаний assistant_scheduler, без них нет schedule_* и раздела «Расписания»
SCHEDULER_API_KEY=ключ                          # X-API-Key сервиса расписаний; ключ определяет пользователя
SCHEDULER_AMQP_URL=amqp://schedule-sumarokov:пароль@localhost:5672/assistant  # запуски по расписанию; с SCHEDULER_QUEUE — обе или ни одной
SCHEDULER_QUEUE=schedule.sumarokov              # очередь «пора» этого пользователя (exchange schedule-due сервиса assistant_scheduler)
MCP_STATIC_KEY=ключ                             # ядро MCP: Authorization: Bearer <ключ>; с TODOIST_TOKEN и DROPBOX_ROOT обязательна для workers.mcp
MCP_HOST=127.0.0.1                              # необязательная (дефолт 127.0.0.1); адрес ядра MCP
MCP_JOURNAL_FILE=/path/to/requests.jsonl        # ядро MCP: журнал запросов (JSON-строка на запрос); обязательна для workers.mcp
MCP_ALLOWED_PROJECTS=assistant                  # необязательная; проекты, разрешённые параметром project (через запятую); пусто — любой отклоняется
MCP_PORT=8790                                   # необязательная (дефолт 8790); порт ядра MCP
PA_WORK_DIR=/tmp/personal_assistant/files       # необязательная (дефолт — <tempdir>/personal_assistant/files); рабочая папка файлов, уборка через сутки
```

Обязательны на старте бота: `OWNER_TELEGRAM_ID`, `BOT_TOKEN`, `BOT_DB_URL`, `REDIS_URL`, `AI_DB_URL`, `AI_MODEL`,
`ATTACHMENTS_S3_*`; `WIKI_DIR` и `WIKI_REMOTE_URL` — при `MEMORY_STORAGE=wiki` (иначе `WIKI_*` необязательны). `CASES_*`, `SCHEDULER_API_*`, `TODOIST_TOKEN`, `GMAIL_*`, `WHATSAPP_MACOS_SNAPSHOT_DIR` и `TELEGRAM_USER_SECRETS_FILE` в коде бота необязательны (нет — нет инструментов),
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
  Объекты бакета библиотека не удаляет — `/clear` чистит историю, не бакет. Вложение из чата модель берёт в работу
  через `file_take(source=chat)` (см. «Файлы»): `ChatAttachments` читает историю треда `str(user_id)`
  (`PostgresMemoryStore(AI_DB_URL)`, окно — вся история треда; адрес — имя вложения или ключ S3), байты — тот же
  `S3AttachmentStore`.
  Текстовые `.txt/.md/.csv` в S3 не попадают — их `file_take(source=chat)` не найдёт
- Имя вложения — в тексте сообщения: хендлер ставит перед подписью владельца по строке «[вложение: <имя>]» на
  каждое (`src/chat/handlers/attachment_labels.py`), так модель видит адрес для `file_take`. Фото имени не имеет —
  `PhotoMessageHandler` сам даёт `photo_<8 hex>.jpg` и кладёт его в `Attachment.filename` (ключ S3 ai_framework
  назначает позже, при сохранении); документ — исходное имя. Старые фото истории (`filename` null) адресуются по
  `photo_<ключ8>.jpg` и ключу
- Альбом Telegram присылает отдельными update с общим `media_group_id`. `PhotoMessageHandler` копит такие фото в
  `AlbumBuffer` (`src/chat/albums/`, ключ — chat_id + media_group_id) и через `ALBUM_QUIET_SECONDS` (1,2 с) тишины
  после последнего фото группы отдаёт их одним запросом: все фото по порядку message_id, подпись альбома (Telegram
  кладёт её в одно фото), одно «Думаю...». Фото без `media_group_id` уходит сразу
- Запросы одного треда к модели идут по очереди: `SendToAgentAction` держит lock на thread_id, новый запрос ждёт
  ответа предыдущего (иначе на тред стартуют две параллельные сессии CLI); разные треды друг друга не ждут

## Файлы

Одна механика для файла из любого места: письмо Gmail, WhatsApp, Dropbox, чат. Сборка — `workers/bot/file_tools_factory.py`
(`file_take`, `file_read`, `file_view`, `file_send`), почтовые черновики — `gmail_tools_factory.py`, `dropbox_save` —
`build_dropbox_save_tool` в `__main__.py`. Код — `src/files/`.

- **Рабочая папка** — `PA_WORK_DIR`, по умолчанию `/tmp/personal_assistant/files` (`tempfile.gettempdir()`), в контейнере
  без тома: файлы живут сутки, перезапуск контейнера переживать им не нужно. `WorkFolder` кладёт файл в
  `<file_id>/<имя>` рядом с `.work_file.json` (имя, тип, размер, источник), каталоги 0700, файлы 0600; `file_id` —
  8 hex-символов. Каталог создаётся при первом `file_take`
- `file_take` (`telegram` — `message_id` + `attachment_id` из `read_telegram`, только при файле
  `TELEGRAM_USER_SECRETS_FILE`; `mail` — `message_id` + `attachment_id` из `read_mail`; `dropbox` — `path` через `DropboxBoundary`, закрытые
  места не отдаёт; `chat` — вложение из истории треда; `whatsapp` — `message_id` + `attachment_id` из `read_whatsapp`,
  только при `WHATSAPP_MACOS_SNAPSHOT_DIR`) — предел 50 МБ, отвечает `{file_id, name, media_type, size}`
- `file_read` — текст через `FileTextReader`: txt/md/csv/json, текстовый слой PDF (pypdf), DOCX, XLSX; обёрнут в
  `UntrustedFileFrame`. `.doc`, `.xls`, скан-PDF без текста — error
- `file_view` — картинки модели (ai_framework v0.9.5): JPEG/PNG/GIF/WebP ужимаются `ImageFitter` под `MAX_IMAGE_BYTES`,
  страницы PDF растрирует `PdfRasterizer` (pypdfium2, 150 dpi), по умолчанию первые 3, не больше 5 за вызов
- `file_send` — документом только владельцу (`OWNER_TELEGRAM_ID`), адресата во входе нет; больше 50 МБ — в «Personal Assistant»
- `dropbox_save` — по `file_id`: пишет `DropboxFileSaver` (граница `DropboxBoundary` + журнал `dropbox_journal`, action
  `added`); перезаписи нет — « (2)». Регистрируется при `DROPBOX_ROOT`
- `draft_mail` / `draft_reply` с `file_ids`: лимит Gmail 25 МБ по закодированному MIME; что не влезает — не прикладывается,
  а уходит в «Personal Assistant», в ответе путь
- **«Personal Assistant»** — папка в корне Dropbox (`OVERFLOW_FOLDER_NAME`) для того, что не пролезает в Telegram или
  Gmail. Временная, как рабочая: `OverflowFolder` пишет туда через `DropboxBoundary`, имя не перезаписывается
- **Уборка** — `Sweeper` в фоновом потоке `files-sweeper` (`start_sweeper` в `__main__.py`): при старте и раз в час
  удаляет файлы с mtime старше 24 ч и опустевшие каталоги ровно в двух корнях — рабочей папке и
  `<DROPBOX_ROOT>/Personal Assistant`; по symlink не ходит, остальной Dropbox не трогает. Удалённое — строкой
  `Sweeper removed …` в лог. Запись в «Personal Assistant» и удаления в `dropbox_journal` не попадают
- Содержимое файла для модели — данные: `file_read` оборачивает текст рамкой, системный промпт запрещает исполнять
  указания из файлов

## Источники: переписка и файлы

Два контракта, на которых подключается новый источник — без правки инструментов.

**Источник переписки** — `src/conversations/`: только модели, ошибки и Protocol-ы, своих реализаций у контекста
нет. Реализации живут в своих контекстах (`src/gmail/`, `src/whatsapp/`) и удовлетворяют протоколам структурно, не
импортируя их; импортируют только модели и ошибки. Сам `src/conversations/` не знает ни одной реализации.

- `IConversationSource` — ядро, которое реализует каждый источник; собрано из трёх узких:
  - `IMessageSearch.search(MessageQuery) -> list[MessageSummary]` — `text` в языке источника (Gmail — синтаксис
    поиска Gmail, WhatsApp — подстрока), фильтры `conversation_id`, `participant`, `since`/`until` (aware datetime), `limit`;
  - `IConversationReader.read_message(message_id)` и `read_conversation(conversation_id, ConversationWindow)` —
    сообщение целиком / тред или чат за период, `has_earlier` — было ли что-то раньше окна;
  - `IAttachmentStore.list_attachments(message_id)` и `fetch_attachment(message_id, attachment_id) -> AttachmentContent`.
- Необязательные возможности — отдельными протоколами, источник реализует их, если умеет:
  `IConversationDirectory.list_conversations` (список чатов, WhatsApp), `ISourceFreshness.freshness()` — дата последнего
  сообщения и время снимка для фразы «последнее сообщение от <дата>» (WhatsApp).
- Поле `date` в моделях — строка, как дату показывает источник (заголовок Date у Gmail, «ДД.ММ.ГГГГ ЧЧ:ММ» у
  WhatsApp): её читает модель. Машинные даты — только в `MessageQuery`, `ConversationWindow`, `SourceFreshness`.
- `ConversationAttachment.availability` — `available` (файл у источника), `on_request` (источник скачает его при
  `fetch_attachment`), `unavailable` с `unavailable_reason`; `fetch_attachment` недоступного или не скачавшегося
  бросает `AttachmentNotDownloadedError` с причиной и подсказкой владельцу. Остальные ошибки —
  `ConversationNotFoundError`, `MessageNotFoundError`, `AttachmentNotFoundError`, общий предок `ConversationSourceError`.
- В протоколе нет отправки: бот в переписку ничего не пишет. Черновики Gmail (`draft_*`) остаются Gmail-специфичными.
- Инструменты модели держат свои узкие Protocol-ы в `src/ai_tools/<tool>/protocols/` (Protocol живёт у клиента), а
  модели и ошибки берут из `src.conversations`. Текст сообщений — в рамке недоверенных данных, как у почты.

### WhatsApp (macOS Desktop)

`src/whatsapp/` — только платформенные реализации протокола источника переписки; вне подпакета
платформы ничего платформенного нет. Linux-вариант для серверов с копиями ассистента встанет
рядом отдельной реализацией того же протокола — без правки инструментов и `file_take`.

`src/whatsapp/macos_desktop/` читает снимок, который делает хост-процесс (см. «Снимок WhatsApp
(хост-процесс)»). Вход — `WhatsAppConversationSource(snapshot_dir, timezone)`
(`services/conversation_source/`): `IConversationSource` + `IConversationDirectory` +
`ISourceFreshness`.
- База — только `file:<снимок>/ChatStorage.sqlite?mode=ro&immutable=1`, соединение на вызов.
  Живую базу из `~/Library/Group Containers` бот не открывает никогда
- Схема Core Data недокументирована: `SnapshotSchema` сверяет нужные колонки при каждом
  соединении — после обновления WhatsApp получаешь `WhatsAppSchemaError` с именами колонок, а
  не пустой ответ. Нет снимка — `WhatsAppSnapshotMissingError`
- id — `Z_PK` строкой (чат, сообщение, медиа); даты — секунды от 01.01.2001 UTC (`CoreDataClock`),
  наружу — «ДД.ММ.ГГГГ ЧЧ:ММ» во временной зоне владельца
- Вложение — `ZFILESIZE > 0` или путь в `ZMEDIALOCALPATH` (превью ссылок — не вложение).
  Скачано — файл есть в `<снимок>/Message/<ZMEDIALOCALPATH>`. Desktop хранит только скачанное (автозагрузка
  фактически выключена), остальное бот качает сам — `services/remote_media/` (решение владельца 28.09.2026):
  - `ZWAMEDIAITEM.ZMEDIAURL` — ссылка на CDN, берётся только `https://mmg.whatsapp.net` (остальные URL в
    колонке — превью ссылок из чатов, по ним бот не ходит); параметр `oe=` — срок жизни ссылки, hex unix time,
    живёт ~30 дней. `ZMEDIAKEY` — protobuf, поле 1 — 32-байтный media key
  - Шифрование медиа WhatsApp (`services/media_cipher/`): HKDF-SHA256 от media key (112 байт, info по типу —
    `WhatsApp Image/Video/Audio/Document Keys`, таблица `services/entities/media_kind.py`) → iv, cipherKey,
    macKey; файл — AES-256-CBC, последние 10 байт — HMAC-SHA256(iv + шифртекст). Запрос — обычный GET без
    аккаунта; тело больше `ZFILESIZE` + 26 не дочитывается, размер после расшифровки сверяется с `ZFILESIZE`
  - Скачивание только по `fetch_attachment` на конкретное вложение, не массово. Расшифрованное ложится в кэш
    `<PA_WORK_DIR>/whatsapp-media/<media_pk>-<хеш ключа>` (снимок только на чтение) и живёт, как рабочая папка,
    сутки (`Sweeper`)
  - Пометка вложения: файл в снимке или в кэше — `available`; ссылка живая — `on_request`; `oe` в прошлом —
    `unavailable` «ссылка истекла» (с запасным путём WhatsApp Web у документа — `on_request`), без
    ссылки/ключа/известного типа — «нет ссылки для скачивания».
    Неудача скачивания — `AttachmentNotDownloadedError` с причиной (ссылка истекла / CDN ответил кодом /
    MAC не сошёлся / размер не сошёлся) и просьбой скачать файл в WhatsApp Desktop; сетевой сбой (таймаут,
    DNS) — исключение httpx, `ai_framework` отдаёт его модели текстом, промпт велит повторить раз
  - Запасной путь — WhatsApp Web (`src/whatsapp/web_media/`, клиент `WhatsAppWebClient`, httpx, таймаут 150 с;
    решение владельца 28.09.2026 — только документы). Включается, если задан `WHATSAPP_WEB_URL` (ключ —
    `WHATSAPP_WEB_TOKEN`, заголовок `Authorization: Bearer`); без URL поведение прежнее. У документа (тип 8, есть
    имя и jid чата; имя — `ZTITLE`, иначе однострочный `ZWAMESSAGE.ZTEXT`: Desktop кладёт имя документа туда,
    часто без расширения — сервис сопоставляет его с показанным «имя.расширение») ссылка истекла по `oe=` или
    CDN ответил 403/404/410 — `POST /v1/documents/fetch` (`chat_title`, `chat_jid`, `file_name` = это имя, `size` = `ZFILESIZE`, `sent_at` UTC); 200 — байты, размер
    сверяется с `ZFILESIZE`, ложатся в тот же кэш, что у CDN. Отказ сервиса (409 не привязан — код придёт в
    Telegram, 504 телефон не ответил, 404 не найден, 502 изменился интерфейс Web) — `AttachmentNotDownloadedError`:
    причина CDN + причина Web словами + `detail` сервиса. Сервис не ответил (connect error, таймаут) — причина
    CDN + «запасной путь WhatsApp Web не ответил». Фото, видео, голосовые с CDN 410 — прежнее поведение.
    Протокол запасного источника — у потребителя (`remote_media/protocols/i_document_fallback.py`),
    `web_media` о `macos_desktop` не знает
- Свежесть — `max(ZMESSAGEDATE)` и `snapshot_at`: бот говорит «последнее сообщение от <дата>»
- Поиск — подстрока без учёта регистра (Python `casefold` через `create_function`, SQLite LIKE
  кириллицу не складывает), полный проход ~0,2 с на 62 тыс. сообщений
- Тесты — только на синтетической базе (`tests/whatsapp/macos_desktop/synthetic_snapshot.py`);
  копии настоящей переписки в репу не кладутся
- Границы держит import-linter: `src.conversations` не импортирует соседей, `src.whatsapp` из соседей знает
  только `src.conversations`

**Источник файлов** для `file_take` — `src/files/sources/protocols/i_file_source.py`:
`IFileSource.fetch(FileRequest) -> FetchedFile`. `FileRequest` — один вход для любого источника: `thread_id` (тред
владельца из контекста), `message_id` + `attachment_id` (вложение переписки: почта, WhatsApp), `path` (хранилище:
Dropbox), `name` (вложение чата по имени). Источник берёт свои поля, недостающие — `FileRequestIncompleteError` с
подсказкой, какие поля нужны; нет файла — `SourceFileNotFoundError`, больше предела — `SourceFileTooLargeError`.
`FetchedFile.origin` — ссылка на место в источнике для `.work_file.json` (`mail:<id>/<attachment>`, `dropbox:<path>`).
Вложения любого источника переписки становятся файлами через одного адаптера над `IAttachmentStore` — отдельный
файловый источник на каждый мессенджер не нужен.

Подключить новый источник:
1. переписка — контекст `src/<источник>/` с репозиторием, реализующим `IConversationSource` (и, если умеет,
   `IConversationDirectory`/`ISourceFreshness`) на моделях `src.conversations.models`; тесты — на синтетических данных;
2. файлы — зарегистрировать источник в `workers/bot/file_tools_factory.py` под новым ключом `source` (для переписки —
   адаптер вложений над её `IAttachmentStore`); `file_take` не правится;
3. инструменты модели и раздел промпта — в `src/ai_tools/` и `data/system_prompt.txt`, регистрация в composition root
   при заданной конфигурации источника.

### Telegram владельца (MTProto)

`src/telegram_user/` — переписка Telegram от имени аккаунта владельца через Telethon (MTProto user API):
Bot API видит только чаты бота. Вход — `TelegramConversationSource.from_secrets_file(path, timezone)`
(`services/conversation_source/`): `IConversationSource` + `IConversationDirectory`, без `ISourceFreshness`.

- Только чтение: `send_*`, `read_acknowledge`, `edit_*`, `delete_*` не вызываются нигде; клиент —
  `receive_updates=False`, после каждого вызова `account.UpdateStatusRequest(offline=True)`. Каналы (broadcast)
  отброшены в списке чатов, поиске и чтении; секретные чаты через API недоступны
- Telethon живёт в своём event loop в потоке `telegram-user` (инструменты вызываются изнутри чужого loop),
  подключение ленивое, на первый вызов; таймаут запроса 300 с
- Файл секретов читается сразу на старте (кривой — `TelegramSecretsFileError`, без значений в тексте)
- telethon импортируется только внутри `src.telegram_user` (import-linter, прямой импорт; composition root
  получает его косвенно через коннектор), сам коннектор из соседей знает только `src.conversations`
- Сессию владелец кладёт в pass `assistant/personal_assistant/telegram-user` скриптом
  `scripts/telegram_login.py`; приложение my.telegram.org — запись `telegram-app`

## Уведомления агентов

Рабочие агенты владельца публикуют уведомления в RabbitMQ на Mac mini, бот пересылает их владельцу и пишет в журнал.
Канал односторонний: ответа отправителю нет, входящего порта у бота нет. Топология и учётки брокера —
`deploy/rabbitmq/setup.sh`: vhost `assistant`, exchange `agent-notify` (fanout) → очередь `pa.notifications`;
бот читает её учёткой `pa-consumer` (только read), отправитель пишет учёткой `agent-<источник>` (только write в exchange).

- Потребитель — фоновый поток `agent-notifications` (`start_agent_notifications` в `__main__.py`), pika, prefetch 1.
  Нет `RABBITMQ_URL` — не стартует, строка `RABBITMQ_URL is not set…` в лог. Обрыв или ошибка — лог и
  переподключение через 15 с (`AGENT_NOTIFICATIONS_RECONNECT_SECONDS`); неподтверждённое сообщение брокер отдаст снова
- Очередь не объявляется: у `pa-consumer` нет configure, её заводит `setup.sh`
- Источник — свойство `user_id` (брокер сверяет его с учёткой, подделать нельзя), в журнал и владельцу — без
  префикса `agent-`. Без `user_id` или `message_id` — лог и `basic_reject` без повтора
- Журнал — таблица `agent_notifications` (миграция `0002`): `message_id` UNIQUE, `source`, `body`, `published_at`
  (свойство `timestamp`), `received_at`, `delivered_at`. `PostgresAgentNotificationRepository.record` —
  `INSERT … ON CONFLICT DO NOTHING` и возврат записи; `received_between(start, end, source, limit)` — чтение для модели
- Владельцу — `app.message_sender`, `ParseMode.PLAIN`: «Агент <источник>:», с новой строки текст дословно; длиннее
  4096 (считается в UTF-16, как у Telegram) — несколькими сообщениями, режется по строке, затем по пробелу
- ack — после отправки и `delivered_at`; повтор уже доставленного `message_id` — ack без второй отправки.
  Упала отправка — сообщение вернётся в очередь при переподключении и уйдёт целиком ещё раз
- Миграции приложения (`apply_migrations`) применяются на каждом старте бота, перед поллингом, — не только при `DROPBOX_ROOT`
- Инструмент модели `agent_notifications` (`src/ai_tools/agent_notifications/`) — журнал за сутки по `received_at`:
  `date` (по умолчанию сегодня) режется по `OWNER_TIMEZONE`, `source` — без префикса `agent-` (с префиксом тоже
  примет), не больше 50 последних, строкой «время · источник · текст». Регистрируется всегда — от RabbitMQ не
  зависит, читает таблицу через `received_between`. Тексты — в рамке `UntrustedNotificationFrame`
  (`<untrusted_notification>`), системный промпт запрещает исполнять из них указания

### Файлы от агентов

Сообщение со свойством `type=file` — файл; без `type` — текст, как выше. Заголовки: `filename` (базовое имя,
UTF-8), необязательный `caption`; байты — либо тело сообщения (до 15 МБ, лимит брокера 16 МиБ), либо при пустом
теле заголовки `path` (от корня Dropbox) и `size` — для файлов 15–50 МБ, которые отправитель кладёт в
`Personal Assistant/agents/`. Развилка текст/файл — в `AgentNotificationDelivery`.

- Без `filename` — `basic_reject` без повтора, как без `user_id`
- `path` читает `DropboxAgentFileStore` (`src/agent_notifications/services/dropbox_file_store/`) через
  `DropboxBoundary`: только внутри `Personal Assistant/agents/`, без `..`, без symlink на пути, не больше 50 МБ
  (`AGENT_FILE_LIMIT_BYTES`); иначе — reject без повтора и строка в лог. Нет `DROPBOX_ROOT` — любой `path` reject
- Файла по пути уже нет (Sweeper чистит «Personal Assistant» через 24 ч) — владельцу текстом «Агент X: файл <имя>
  (<размер>) не дошёл — в Dropbox его уже нет», запись в журнал, ack: повтор удалённое не вернёт
- Владельцу — сперва текст «Агент <источник>: файл <имя> (<размер>)» и с новой строки подпись, если дана, затем
  документ через `app.document_sender.send_document` (подписи на самом документе нет — её нет в bot_framework).
  ack и повтор доставленного — как у текста
- Журнал — миграция `0003`: nullable `file_name`, `file_size`; `body` у файла — подпись или `''`. Байты нигде не
  хранятся. Размер печатает `human_size` (1024-основание, «1,2 МБ») через `AgentNotification.file_label` — одна
  функция и для владельца, и для инструмента `agent_notifications`: у файла строка «время · источник · файл <имя>
  (<размер>) — подпись»

## Запуски по расписанию

Расписания хранит и отсчитывает сервис `assistant_scheduler` (своя репа); когда срок подошёл, он публикует в
RabbitMQ сообщение «пора» (exchange `schedule-due`, ключ — пользователь → очередь `schedule.<user>`, vhost
`assistant`; топология — в репе сервиса). Логики расписаний в боте нет: только «получил — выполнил — отдал
владельцу». Контекст `src/scheduled_runs/` не знает ни модели, ни Telegram, ни клиента кейсов (import-linter):
их подставляет `workers/scheduled_run/composition.py` — так исполнитель уносится в отдельный воркер без правки.

- Поток `scheduled-runs` (`start_scheduled_runs`), стартует внутри `with ai:` бота. Нет `SCHEDULER_AMQP_URL` и
  `SCHEDULER_QUEUE` — не стартует, строка `…scheduled runs are off` в лог; задана одна из двух — бот падает на старте.
  Очередь не объявляется. pika, prefetch 1, обрыв — лог и переподключение через 15 с. Сердцебиение AMQP выключено
  (`heartbeat=0`): прогон модели идёт минуты внутри обработчика, а `BlockingConnection` там сердцебиение не шлёт
- Контракт — таск цикла опроса сервиса: свойства `message_id` = id запуска, `user_id` = учётка брокера `scheduler`,
  `type` = `schedule.due`; тело JSON v1 (`ScheduleDue`): `run_id`, `schedule_id`, `user`, `case_id`,
  `task_event_id?`, `instruction`, `kind` (`once|periodic`), `cron?`, `timezone` (IANA), `scheduled_for`, `fired_at`
  (с поясом), `late`. `user_id` не `scheduler`, другой `type`, нет `message_id` или он ≠ `run_id`, тело не по
  схеме — лог и `basic_reject` без повтора
- Журнал — `scheduled_runs` (миграция `0005`): `run_id` UNIQUE, `schedule_id`, `case_id`, `started_at`,
  `finished_at`, `delivered_at`, `error` (тип ошибки прогона). Доставленный `run_id` пришёл снова — ack без прогона;
  недоставленный (упали посреди) — прогоняется заново
- Прогон — отдельный `AIApplication` (`build_scheduled_run_ai`), тред `schedule:<run_id>`, промпт —
  системный промпт бота (с теми же разделами коннекторов) и `data/schedule_run_prompt.txt` после него, на каждый
  прогон заново (дата). Запрос: id запуска, вид расписания, время срабатывания в поясе расписания (и опоздание),
  инструкция владельца, кейс в виде `case_read` (последние 50 событий, рамка `UntrustedCaseFrame`). Кейс не
  прочитался или нет `CASES_*` — прогон идёт без ленты, так и сказано в запросе. `tool_context` — чат владельца
- Инструменты — все инструменты бота, кроме `colleague_send` и любых `schedule_*` (`scheduled_run_tools`, решение
  владельца 01.10.2026): владельца в разговоре нет, подтвердить отправку коллеге некому, и расписание не плодит
  расписаний. Промпт велит записать итог в ленту кейса: `case_add_event`, source `assistant`,
  source_ref `run:<id>:result`
- Владельцу — `app.message_sender`, `ParseMode.PLAIN`, длинное режет `TelegramTextSplitter`: «По расписанию ·
  <название кейса>:» и с новой строки ответ; при `late` — «(с опозданием на N мин)» после названия (N — от
  `scheduled_for` до `fired_at`). Сбой прогона — «Запуск по расписанию не выполнился: <тип ошибки>» и строка с
  кейсом и инструкцией. ack — после отправки и `delivered_at`; упала отправка — сообщение вернётся, прогон повторится
- Тест миграции (`tests/scheduled_runs/test_scheduled_runs_migration.py`) идёт на `TEST_DATABASE_URL` — отдельной
  пустой базе; без переменной пропускается

### Заведение расписаний (инструменты)

Заводит, показывает и отменяет расписания модель в разговоре с владельцем — через HTTP API того же сервиса
(контракт — таск 01a0f0c3-7380 и CLAUDE.md репы `assistant_scheduler`). Пользователь — из ключа
(`SCHEDULER_API_KEY`), чужое расписание отвечает 404, как несуществующее.

- Клиент — `src/scheduler/repos/scheduler_http_client.py` (`SchedulerHttpClient`, httpx, `X-API-Key`):
  `POST /schedules` (тело без пустых полей), `GET /schedules` (`status`, `case_id`, `limit`), `POST /schedules/{id}/cancel`.
  Граница — import-linter «scheduler client stands alone»: `src.scheduler` не знает ни соседей, ни модели, ни Telegram
- Ошибки — `src/scheduler/errors/`, общий предок `SchedulerServiceError`, текст — указание модели: 401 →
  `SchedulerUnauthorizedError`; 404 `schedule_not_found` / `case_not_found` → `ScheduleNotFoundError` /
  `ScheduleCaseNotFoundError` («найди кейс через case_find»); 409 `schedule_finished` → `ScheduleFinishedError`;
  422 `too_frequent` → `TooFrequentError` (порог из ответа), `limit_reached` → `LimitReachedError` (лимит из ответа),
  `validation` с `detail[0].type` `in_past` / `never_fires` → `ScheduleInPastError` / `ScheduleNeverFiresError`, иначе
  `SchedulerValidationError`; 503 `cases_unavailable` → `CasesUnavailableError`; прочее ≥ 400 → `SchedulerFailureError`;
  сеть/таймаут → `SchedulerUnavailableError`. Инструменты отвечают модели `{"error": …}`
- `schedule_add` (case_id — id из `case_find` или `inbox`, instruction, `at` | `cron`, timezone — умолчание
  `OWNER_TIMEZONE`): ровно одно из at/cron и известный IANA-пояс проверяются до запроса; `at` без пояса — в поясе
  timezone (то есть владельца). Ответ — id и ближайшие срабатывания из `upcoming` в поясе владельца («пт 02.10.2026
  10:00»), у периодического — до трёх
- `schedule_list` (case_id, status — умолчание `live`) — строки «id · [статус] · когда · кейс · инструкция», статус —
  если не active; когда — момент разового или «cron … (пояс), ближайшее …». Названия кейсов — одним `find_cases`
  (status all, 100) клиента кейсов; кейсов нет или сервис лёг — вместо названия case_id
- `schedule_cancel` (schedule_id) — `POST …/cancel`; отменённое повторно — 200
- Регистрация — `workers/bot/scheduler_tools_factory.py` при `SCHEDULER_API_URL` и `SCHEDULER_API_KEY`; задана одна из
  двух — бот падает на старте. Есть клиент — в промпте остаётся раздел «Расписания» (`connector:scheduler`): кейс —
  сперва `case_find`, естественный язык → at/cron (`1#1` — первый понедельник), очевидное не переспрашивать, ответ —
  ближайшие срабатывания из ответа инструмента. «Напомни позвонить» (шаг владельца) — задача, «напиши мне в срок» и
  «проверь в срок» — расписание
- Имена начинаются с `schedule_` — по префиксу их отсекает прогон по расписанию (`scheduled_run_tools`)

## Почта ассистентов

Ассистенты сотрудников одной компании пишут друг другу через RabbitMQ на Mac mini, а не через мессенджеры.
Топология и учётки — `deploy/rabbitmq/assistants.sh`: vhost на компанию (`assistants.sumarokov`), exchange
`assistant-mail` (direct, ключ маршрута — ключ адресата) → ящик `inbox.<ключ>`; учётка `assistant-<ключ>` пишет в
exchange любому коллеге и читает только свой ящик. Контекст `src/colleague_mail/` модели не знает (контракт
import-linter запрещает ему `ai_framework` и `bot_framework`): инструменты модели и сводка владельцу — поверх него.

- Нет `ASSISTANT_MAIL_URL` и `ASSISTANT_KEY` — ни приёма, ни отправки, строка `…colleague mail is off` в лог. Задана
  одна из двух — бот падает на старте; логин URL не `assistant-<ASSISTANT_KEY>` — тоже (`ColleagueMailSettings`)
- Формат v1: свойства AMQP `message_id`, `user_id` (учётка, брокер сверяет с логином), `timestamp`, `type`; тело JSON
  `{v:1, from, to, type, text, in_reply_to?, about_agent?}` (`MailBody`), `type` — `remark|question|answer`, ключи — `^[a-z0-9][a-z0-9-]*$`
- Отправка — `ColleagueMailSender.send(OutgoingMail) -> SendResult(message_id, outcome)`, сборка —
  `build_colleague_mail_sender` в `__main__.py`. `RabbitMqMailPublisher`: соединение на вызов, publisher confirms +
  `mandatory`. Итог `MailSendOutcome`: `in_recipient_inbox` (брокер подтвердил), `no_recipient` (basic.return — ящика
  такого ключа нет), `broker_unavailable` (нет связи, nack, отказ). В журнал ложится только дошедшее
- Приём — фоновый поток `colleague-mail` (`start_colleague_mail`), `inbox.<ASSISTANT_KEY>`, prefetch 1, переподключение
  через 15 с. **Входящее только пишется в журнал** — модели и владельцу приём ничего не отдаёт; ack после записи,
  повтор `message_id` — ack без второй записи. Нет `message_id`/`user_id`, учётка не `assistant-…`, тело не по схеме,
  `from` ≠ `user_id` без `assistant-` или `to` ≠ свой ключ — лог и `basic_reject` без повтора
- Журнал — `colleague_messages` (миграция `0004`), `PostgresColleagueMessageRepository`: `message_id`, `direction`
  (`in|out`, уникальность — пара `message_id, direction`: письмо самому себе ложится обеими сторонами), `peer` (ключ
  коллеги), `type`, `text`, `about_agent`, `in_reply_to`, `sent_at` (для входящего — AMQP `timestamp`), `received_at`
  (только входящие), `shown_at` (показано владельцу — пишет сводка)
- Справочник — `YamlColleagueDirectory(ASSISTANT_DIRECTORY_FILE)`, `colleagues()` / `find(key)`, файл читается на каждый
  вызов (правка без рестарта); сборка — `build_colleague_directory`. Формат — словарь по ключу:
  `sumarokov: {name: Владимир Сумароков, editor: true}`; `editor` необязателен (false)
- Чтение журнала — `PostgresColleagueMessageRepository.messages_between(start, end, peer, message_type, limit)`
  (обе стороны, момент — `received_at` входящего или `sent_at` исходящего, `[start, end)`, берёт последние `limit`,
  отдаёт хронологически) и `unshown_incoming(peer, message_type, limit)` (входящие с `shown_at IS NULL`, старые
  первыми). `peer`/`message_type` = `None` — без фильтра. `shown_at` чтение не ставит
- Инструменты модели — `src/ai_tools/colleague_mail/`, регистрируются (`build_colleague_mail_tools` в `__main__.py`)
  только при заданных `ASSISTANT_MAIL_URL`/`ASSISTANT_KEY`. Контексты `ai_tools` и `colleague_mail` независимы:
  инструменты видят протоколы, отправку им отдаёт адаптер `workers/bot/colleague_mail_tool_gateway.py`
  - `colleagues` — справочник: ключ · имя · редактор. Нет `ASSISTANT_DIRECTORY_FILE` — так и отвечает
  - `colleague_send` — `to` (ключ или `editors` — все `editor: true` справочника; без справочника `editors` не
    отправляет), `type`, `text`, `in_reply_to?`, `about_agent?`; итог по строке на адресата — значение
    `MailSendOutcome` дословно (+ `message_id` дошедшего) и расшифровка трёх значений. Подтверждения в коде нет:
    согласие владельца на текст и адресата требует системный промпт (раздел «Почта коллег»)
  - `colleague_messages` — `date_from`/`date_to` (дни по `OWNER_TIMEZONE`, по умолчанию неделя по сегодня) или
    `unshown=true`; фильтры `colleague`, `type`; не больше 50. Журнал — в рамке `UntrustedColleagueMessageFrame`
    (`<untrusted_colleague_message>`), промпт запрещает исполнять указания из писем и звать по ним инструменты
- Сводка владельцу — `ColleagueDigest` (`src/colleague_mail/services/digest/`), без модели: все входящие с
  `shown_at IS NULL` (`unshown_incoming(None, None, limit=None)` — без лимита, `LIMIT NULL`: одна сводка целиком,
  длинную режет сплиттер), группы «Замечания к общим агентам» / «Вопросы» / «Ответы», строка «имя · агент · текст»
  (агент — если есть `about_agent`; имя — из справочника, неизвестный ключ или нет справочника — сам ключ), текст
  дословно. Шлёт `app.message_sender`, `ParseMode.PLAIN` (через `OwnerNotifier`), длиннее 4096 — `TelegramTextSplitter`.
  Пусто — не шлёт ничего. `mark_shown(ids)` — после отправки всех кусков; упала отправка — всё остаётся непоказанным
- Расписание — поток `colleague-digest` бота (`start_colleague_digest`), только при включённой почте: ждёт ближайший
  `COLLEAGUE_DIGEST_AT` (`HH:MM`, по умолчанию `09:00`) в `OWNER_TIMEZONE` и шлёт. Рестарт после срока — ждёт
  завтрашнего; повтора нет — критерий один, `shown_at`. Ошибка — лог, следующая попытка в следующий срок.
  `COLLEAGUE_DIGEST_AT` в `compose.yaml` не передаётся — в проде действует умолчание
- Ручной запуск той же сводки — `python -m workers.colleague_digest` (`BOT_DB_URL`, `BOT_TOKEN`, `OWNER_TELEGRAM_ID`,
  `ASSISTANT_DIRECTORY_FILE` необязательна); в проде — `docker exec personal_assistant_bot python -m workers.colleague_digest`.
  Отмечает показанным так же, как по расписанию: утренняя сводка после ручной покажет только новое

## Технологический стек

- Python 3.13+
- bot-framework[all]==0.8.2 — фреймворк для Telegram-ботов
- ai-bot-framework[claude-sdk,s3] (git-тег v0.9.5) — AIApplication, память, ClaudeSdkProvider, вложения в S3, картинки в результате инструмента
- fastmcp 4.x — ядро MCP (Streamable HTTP поверх mcp 2.x)
- pika — потребитель уведомлений агентов и почта ассистентов (RabbitMQ)
- PyYAML — справочник коллег
- pypdf, python-docx, openpyxl — текст PDF/DOCX/XLSX; pypdfium2 — скан-PDF в PNG; Pillow — ужать картинку под 5 МБ
- uv — управление зависимостями

## Команды

- Установка зависимостей: `uv sync`
- Запуск бота: `uv run python -m workers.bot`
- Запуск ядра MCP: `uv run python -m workers.mcp`
- Проверки: `uv run ruff check .`, `uv run mypy src workers tests scripts`, `uv run lint-imports`, `uv run pytest`

## Deploy

- Рядом с ботом из того же образа — ядро MCP, контейнер `personal_assistant_mcp` (см. «Ядро MCP»), `up.sh`
  выкатывает оба
- Бот работает контейнером в colima на Mac mini (linux/arm64). В образе CLI Claude Code из колеса
  `claude-agent-sdk` со встроенными инструментами, выключенными managed settings (см. выше); git и openssh-client —
  для вики, ключи хоста github.com — из `deploy/ssh/known_hosts` (системный known_hosts); typst и jq нет.
  Деплой — `deploy/up.sh` (скилл `/deploy`), локально, без SSH
- `up.sh` берёт секреты из pass (`assistant/personal_assistant/{bot-token,owner-telegram-id,db,claude-oauth-token,voice-recognition-key,obsidian-wiki-deploy-key,spaces-attachments,todoist-token,gmail-oauth-client,gmail-refresh-token,rabbitmq,cases-api-key,scheduler-api-key,scheduler-amqp,whatsapp-web,telegram-user,telegram-app,mcp-key}`,
  `GNUPGHOME=~/docker/personal_assistant/gnupg` — свой GPG-ключ ассистента), собирает из `db` переменную
  `AI_DB_URL` (`options=-csearch_path%3Dai`), разбирает `spaces-attachments` (первая строка — secret key → `ATTACHMENTS_S3_SECRET_KEY`,
  строки `access_key=`, `bucket=`, `region=`, `endpoint=` → остальные `ATTACHMENTS_S3_*`), из `gmail-oauth-client`
(JSON `client_secret_*.json` целиком) достаёт `installed.client_id`/`installed.client_secret` через `python3` → `GMAIL_CLIENT_ID`/`GMAIL_CLIENT_SECRET`,
первые строки `todoist-token`, `gmail-refresh-token`, `rabbitmq`, `cases-api-key`, `scheduler-api-key` и `scheduler-amqp` → `TODOIST_TOKEN`, `GMAIL_REFRESH_TOKEN`,
`RABBITMQ_URL`, `CASES_API_KEY`, `SCHEDULER_API_KEY`, `SCHEDULER_AMQP_URL` (пустое значение останавливает выкат), и запускает `docker compose -f deploy/compose.yaml up -d --build`.
  Секреты идут переменными окружения, в файлы не пишутся — кроме deploy-ключа вики: ssh читает ключ только из
  файла, `up.sh` кладёт его в `~/docker/personal_assistant/secrets/wiki_deploy_key` (0600, каталог 0700), в
  контейнер он монтируется read-only как `/run/secrets/wiki_deploy_key` (`WIKI_SSH_KEY_PATH`) — и сессии
  Telegram владельца (см. ниже)
- Telegram владельца: `up.sh` собирает файл секретов из pass `telegram-user` (одна строка — StringSession) и
  `telegram-app` (строки `api_id=`, `api_hash=`) — три строки `session=`, `api_id=`, `api_hash=` (формат держит
  `src/telegram_user/repos/telegram_secrets_file.py`), кладёт 0600 (umask 077, `.tmp`, `mv`) в
  `~/docker/personal_assistant/secrets/telegram/telegram_user` (каталог 0700); каталог монтируется
  `/run/secrets/telegram:ro`, `TELEGRAM_USER_SECRETS_FILE=/run/secrets/telegram/telegram_user` (compose).
  Каталогом, а не файлом: нет файла — docker не подставит на его место пустой каталог. Значения идут через
  встроенный `printf` bash — ни в аргументы процессов, ни в вывод. Нет записи `telegram-user` в pass (проверка
  по файлу `.gpg` хранилища, без расшифровки) — прежний файл удаляется, бот стартует без Telegram, выкат
  идёт. Сессию кладёт в pass владелец скриптом `scripts/telegram_login.py`
- Вики: том `~/docker/personal_assistant/wiki` → `/wiki`, `WIKI_DIR=/wiki/obsidian_wiki`; первый clone на пустом
  томе делает сам бот. `WIKI_REMOTE_URL` — `git@github.com:sumarokov-vp/obsidian_wiki.git` (дефолт в compose/up.sh)
- Схему `ai` в БД `personal_assistant` `up.sh` не создаёт — `CREATE SCHEMA IF NOT EXISTS ai` делается один раз
  руками (`docker exec -u postgres postgres psql -U sumarokov -d personal_assistant`), миграции ai_framework её не создают
- Сеть — внешняя `infra`: `postgres`, `redis` по именам. `network_mode: host` в colima указывал бы на Linux-VM, а не на mac
- Сервис кейсов `assistant_cases` — соседний контейнер в сети `infra`, порт на хост не публикуется:
  `CASES_API_URL=http://assistant_cases:8000` (умолчание в `up.sh` и `compose.yaml`). `CASES_API_KEY` — pass
  `cases-api-key`; тот же ключ строкой `user:ключ` лежит в записи `API_KEYS` сервиса кейсов (pass
  `assistant/assistant_cases/api-keys`, основной keyring Mac mini) — новый ключ вступает в силу после `deploy/up.sh`
  сервиса кейсов. Без `CASES_*` бот стартует без инструментов кейсов и задач
- Сервис расписаний `assistant_scheduler` — соседний контейнер в сети `infra`, порт на хост не публикуется:
  `SCHEDULER_API_URL=http://assistant_scheduler:8000` и `SCHEDULER_QUEUE=schedule.sumarokov` — прямо в `compose.yaml`;
  `SCHEDULER_API_KEY` — pass `scheduler-api-key` (тот же ключ строкой `sumarokov:ключ` в pass
  `assistant/assistant_scheduler/api-keys` сервиса), `SCHEDULER_AMQP_URL` — pass `scheduler-amqp` (учётка
  `schedule-sumarokov`, только чтение `schedule.sumarokov` в vhost `assistant`; учётку и очередь заводит
  `deploy/rabbitmq/setup.sh` репы `assistant_scheduler`). На проде все четыре обязательны (`${VAR:?}`): в логе старта
  `AI tools:` с `schedule_add`/`schedule_list`/`schedule_cancel`, `Prompt connectors:` со `scheduler` и поток
  `scheduled-runs`
- Распознавание речи — GPU-сервер по mesh `http://10.72.0.199:8000`, из контейнера достижим
- Dropbox: `~/Dropbox` хоста (синхронизирует Maestral на Mac mini) — том `/dropbox` на запись, `DROPBOX_ROOT=/dropbox`.
  colima отдаёт `$HOME` через virtiofs (`~/.colima/default/colima.yaml`: `mounts: []`), файл из контейнера ложится
  на хост под владельцем, и Maestral его подхватывает как обычную правку. Закрытые папки перекрыты пустым каталогом
  `~/docker/personal_assistant/empty` только на чтение — их содержимого в контейнере нет физически: `Vault`,
  `03_home/07_ecp/egov.kz` (ключи ЭЦП и пароль). `01_work` открыт (решение владельца 26.09.2026). Заглушку создаёт `up.sh` и падает, если она не пуста.
  Новая чувствительная папка в корне Dropbox видна боту, пока её не добавят в оверлеи `compose.yaml`;
  `vault_selftest_*` меняют имена — их отсекает код инструментов Dropbox, не монтирование
- WhatsApp: том `~/docker/personal_assistant/whatsapp` → `/whatsapp:ro`, `WHATSAPP_MACOS_SNAPSHOT_DIR=/whatsapp`
  (compose). Монтируется только снимок хост-процесса, папка WhatsApp (`Group Containers`) — никогда (см. «Снимок
  WhatsApp (хост-процесс)»). Каталог создаёт `host/install.sh`, его зовёт `up.sh`
- WhatsApp Web: не том, а HTTP до хостового сервиса на localhost — `WHATSAPP_WEB_URL=http://host.docker.internal:18790`,
  `WHATSAPP_WEB_TOKEN` из pass `whatsapp-web` (см. «WhatsApp Web (хостовый сервис)»). Устанавливает
  `hosts/whatsapp_web/install.sh`, его зовёт `up.sh`; без ключа в pass ещё не заведён — `install.sh` заводит сам
- В контейнере uid 1000; монтируются том вики, ключ вики и Dropbox: сессии CLI живут в `$HOME/.claude` контейнера
  и пропадают с ним. Рабочая папка файлов — `/tmp/personal_assistant/files` контейнера, без тома (`PA_WORK_DIR` в compose
  не задаётся — дефолт кода); проверить: `docker exec personal_assistant_bot ls -la /tmp/personal_assistant/files`
- `docker compose build` без `up.sh` требует заглушки секретов, compose интерполирует `${VAR:?}` и при сборке:
  `OWNER_TELEGRAM_ID=x TODOIST_TOKEN=x GMAIL_CLIENT_ID=x GMAIL_CLIENT_SECRET=x GMAIL_REFRESH_TOKEN=x BOT_TOKEN=x BOT_DB_URL=x AI_DB_URL=x CLAUDE_CODE_OAUTH_TOKEN=x VOICE_RECOGNITION_API_KEY=x PA_DATA_DIR=x WIKI_DEPLOY_KEY_FILE=x ATTACHMENTS_S3_ENDPOINT=x ATTACHMENTS_S3_BUCKET=x ATTACHMENTS_S3_REGION=x ATTACHMENTS_S3_ACCESS_KEY=x ATTACHMENTS_S3_SECRET_KEY=x DROPBOX_DIR=x RABBITMQ_URL=x ASSISTANT_MAIL_URL=x ASSISTANT_KEY=x ASSISTANT_DIRECTORY_FILE=x CASES_API_KEY=x SCHEDULER_API_KEY=x SCHEDULER_AMQP_URL=x TELEGRAM_SECRETS_DIR=x MCP_STATIC_KEY=x docker compose -f deploy/compose.yaml build`.
  Эта команда перетегирует `personal_assistant-bot:latest`; проверить сборку, не задевая прод, — `docker build -f deploy/Dockerfile -t <свой тег> .`
- Одна копия бота на Telegram-токен: нативный запуск и контейнер одновременно не держать
- Redis база: 4

### Снимок WhatsApp (хост-процесс)

WhatsApp Desktop на Mac mini держит переписку в `~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/`
(`ChatStorage.sqlite` в WAL). **VM colima к этой папке не обращается никогда** — ни `ls`, ни mount в compose:
28.09.2026 одно обращение VM к ней повесило virtiofs целиком (postgres, redis, rabbitmq, `limactl shell`).
Живую WAL-базу через virtiofs читать тоже нельзя: `-shm` и блокировки между macOS и Linux не согласованы.
Бот читает только снимок, который делает хост. Это хостовая часть коннектора «WhatsApp (macOS Desktop)» —
`src/whatsapp/macos_desktop/host/` (не Python-пакет, просто файлы); Linux-вариант для серверов будет отдельной
реализацией того же протокола:

- `src/whatsapp/macos_desktop/host/whatsapp_snapshot.c` + `Info.plist` — бандл
  `~/docker/personal_assistant/bin/WhatsAppSnapshot.app` (исполняемый файл `Contents/MacOS/whatsapp_snapshot`,
  `CFBundleIdentifier` `com.sumarokov.personal-assistant.whatsapp-snapshot`, `LSBackgroundOnly`),
  launchd-агент `com.sumarokov.personal-assistant.whatsapp-snapshot` (`StartInterval` 120, `RunAtLoad`).
  Каждый запуск: открывает базу только на чтение (нет доступа — ошибка в лог, снимок не трогается, метка стареет);
  если mtime/размер `ChatStorage.sqlite` или `-wal` изменились — копия через SQLite backup API во временный файл,
  `journal_mode=delete`, `quick_check`, атомарный `rename`; затем `rsync` `Message/Media/` без `*.thumb`,
  `*.mmsthumb` и `Profile/`; в конце метка `snapshot_at`. Бандл, а не голый бинарь: голому ad-hoc бинарю TCC не
  запоминает решение «данные других приложений» (`auth_value` 5 — диалог на каждый процесс). Прежний голый бинарь
  `~/docker/personal_assistant/bin/whatsapp_snapshot` больше не используется (install.sh его не удаляет)
- Снимок — `~/docker/personal_assistant/whatsapp/`: `ChatStorage.sqlite` (журнал delete, читается `mode=ro` и
  `immutable=1` из каталога без записи), `Message/Media/...` (путь от `Message/` — как в `ZWAMEDIAITEM.ZMEDIALOCALPATH`),
  `snapshot_at` (ISO-8601 UTC — на это время снимок сверен с источником), служебный `.source_stamp`
- Лог — `~/Library/Logs/personal_assistant/whatsapp_snapshot.log`: ошибки и строка на каждую копию базы. Сторож
  `alarm` 100 с: не уложившийся запуск пишет строку «сторож: запуск не завершился за 100 с — вероятно, ждёт
  разрешения macOS (TCC)…» и выходит с кодом 2 (раньше гиб от SIGALRM молча — так выглядит висящий диалог TCC)
- Установка — `src/whatsapp/macos_desktop/host/install.sh` (вызывает `up.sh`, идемпотентно): собирает бандл
  системным `cc` во временный каталог, подписывает ad-hoc весь бандл (`--identifier` = bundle id), подменяет
  прежний; пересборка только при смене хеша исходника, `Info.plist` и флагов сборки/подписи. Кладёт plist в
  `~/Library/LaunchAgents/`, `launchctl bootstrap gui/<uid>`. Нужна GUI-сессия владельца. `--no-load` — собрать и
  положить plist, но launchctl не трогать (установка до выдачи доступа)
- **«Полный доступ к диску»** выдаётся вручную бандлу `~/docker/personal_assistant/bin/WhatsAppSnapshot.app` (не
  `/bin/sh`, не терминалу): Системные настройки → Конфиденциальность и безопасность → Полный доступ к диску → «+» →
  Cmd+Shift+G → путь. `rsync` запускается им дочерним процессом и доступ наследует. Проверка выдачи — запись
  `kTCCServiceSystemPolicyAllFiles` с `auth_value` 2 в `/Library/Application Support/com.apple.TCC/TCC.db`
  (системная база, читается только процессом с FDA). Разрешение привязано к подписи: правка `whatsapp_snapshot.c`
  или `Info.plist` = пересборка = владелец заново выдаёт доступ, поэтому такую правку перед выкатом согласовывать
  с владельцем через главный диалог
- Проверить: `tail ~/Library/Logs/personal_assistant/whatsapp_snapshot.log`, `cat ~/docker/personal_assistant/whatsapp/snapshot_at`,
  `sqlite3 'file:<снимок>?mode=ro' 'pragma integrity_check'`, `max(ZMESSAGEDATE)` (секунды от 01.01.2001).
  Ручной прогон в свой каталог: `~/docker/personal_assistant/bin/whatsapp_snapshot <каталог>`

### WhatsApp Web (хостовый сервис)

Второе связанное устройство аккаунта владельца — не снимок, а живой Chromium под Playwright
(`hosts/whatsapp_web/`, отдельный uv-проект, вне образа бота и его mypy/import-linter/pytest,
см. «Инструменты (tools)» → «WhatsApp» и `hosts/whatsapp_web/README.md`). Бот зовёт его только
запасным путём: документ чата, который WhatsApp уже удалил с CDN, сервис достаёт перезаливкой
через интерфейс WhatsApp Web (владельцу — руками ничего делать не нужно, лишь бы телефон был в
сети). Отправки, чтения переписки и массовой выкачки нет — только скачивание по запросу.

- launchd-агент `com.sumarokov.personal-assistant.whatsapp-web` (`RunAtLoad`, `KeepAlive`, домен
  `gui/<uid>` — Chromium требует GUI-сессии владельца), лог — `~/Library/Logs/personal_assistant/whatsapp_web.log`.
  `ProgramArguments` — `.venv/bin/whatsapp-web-host` (консольный скрипт из `pyproject.toml`), не
  `uv run`: launchd не видит `PATH` пользователя, а venv уже собран `install.sh`
- Рантайм — не в checkout `hosts/whatsapp_web/`, а постоянный каталог
  `~/docker/personal_assistant/whatsapp-web/app` (`APP_DIR`): `install.sh` копирует туда проект
  `rsync --checksum --delete` (исходники, `pyproject.toml`, `uv.lock`; `.venv`, тесты и сам
  `install.sh`/`launchd/` исключены и не удаляются) и собирает там `.venv` (`uv sync --locked
  --no-dev`). Так удаление/переключение worktree или `uv sync` в рабочей копии, из которой
  когда-то ставили сервис, не ломает прод — `ProgramArguments` в plist смотрит в `APP_DIR`, а не в
  checkout. `rsync --checksum` сравнивает содержимое, не mtime: второй прогон, в т.ч. из другой
  рабочей копии с тем же кодом, ничего не копирует и не перезапускает агента; `launchctl kickstart
  -k` идёт, только если rsync реально что-то поменял в `APP_DIR`
- Слушает только `127.0.0.1:18790` (`WHATSAPP_WEB_PORT`, см. README) — из контейнера бота
  `http://host.docker.internal:18790`. Профиль Chromium — `~/docker/personal_assistant/whatsapp-web/profile`
  (0700); первый прогон пробного сценария оставил привязанный профиль в `~/whatsapp-web-spike/profile` —
  `install.sh` переносит его копией (`cp -a`, исходник не трогается) при пустом целевом каталоге,
  предварительно остановив спайк-браузер, если он слушает `:9222`
- Секреты — один файл 0600 `~/docker/personal_assistant/secrets/whatsapp-web` (`WHATSAPP_WEB_KEY_FILE`):
  первая строка — ключ API (`Authorization: Bearer`, тот же в `WHATSAPP_WEB_TOKEN` бота), дальше
  `key=value`: `phone=<номер>` (перепривязка кодом — #01a0e7b6-23e6), `notify_amqp_url=<URL agent-whatsapp-web>`
  (нет строки — сервис не падает, сигнал о перепривязке пишется только в лог). Источник — pass
  `assistant/personal_assistant/whatsapp-web` (ключ, `phone=`, связка ассистента, как у `up.sh`) и
  учётка RabbitMQ `agent-whatsapp-web` (`deploy/rabbitmq/setup.sh add-source whatsapp-web`, vhost
  `assistant`, exchange `agent-notify`) — её pass-запись `work/local/rabbitmq/assistant-notify/whatsapp-web`
  вне связки ассистента (`$ASSISTANT_GNUPGHOME` её не расшифровывает: там только приватный ключ
  ассистента, а `work/` шифруется на YubiKey/soft key), поэтому `install.sh` читает и заводит её
  с явно снятым `GNUPGHOME` (`env -u`), а не с тем, что экспортировал вызвавший `up.sh`
- Установка — `hosts/whatsapp_web/install.sh` (вызывает `up.sh`, идемпотентно): копирует проект в
  `APP_DIR` (`rsync --checksum --delete`), там `uv sync --locked --no-dev`, `playwright install
  chromium`, перенос профиля (если нужен), pass-запись ключа и номера (нет — заводится: ключ
  `openssl rand -hex 32`, номер вытаскивается из `~/whatsapp-web-spike/scripts/s_num.py`, сам
  скрипт не запускается — в репозиторий, лог и очередь номер не попадает), учётка RabbitMQ,
  файл секретов (перезаписывается только при изменении), plist в `~/Library/LaunchAgents/`
  (`ProgramArguments` — путь в `APP_DIR`). `launchctl bootstrap gui/<uid>`: изменился plist —
  `bootout` + `bootstrap`; не изменился, но `rsync` обновил `APP_DIR` — `kickstart -k`; иначе
  без изменений
- Первая проверка привязки — на старте сервиса (`GET /v1/health` до неё сам её делает); дальше
  отдаёт последнее известное состояние, браузер не поднимая. Суточную проверку и сигнал владельцу
  при отвязке (агент-уведомление, код перепривязки) проводит #01a0e7b6-23e6
- Проверить: `launchctl print gui/<uid>/com.sumarokov.personal-assistant.whatsapp-web`,
  `curl -H "Authorization: Bearer <ключ>" http://127.0.0.1:18790/v1/health`,
  `lsof -iTCP:18790 -sTCP:LISTEN` (только `127.0.0.1`), `tail ~/Library/Logs/personal_assistant/whatsapp_web.log`
