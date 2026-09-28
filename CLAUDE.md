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
├── todoist_tools_factory.py # find_tasks, create_task, read_task, add_task_link, update_task поверх TodoistTaskService
├── gmail_tools_factory.py   # search_mail, read_mail, draft_reply, draft_mail поверх GmailClient (OAuth refresh token)
├── whatsapp_tools_factory.py # коннектор WhatsApp по env + search_whatsapp, read_whatsapp, list_whatsapp_chats
├── protocols/               # IWhatsAppSource — что бот берёт от коннектора WhatsApp (протоколы src.conversations)
└── file_tools_factory.py    # file_take (источники регистрацией), file_read, file_view, file_send поверх WorkFolder
src/
├── access/                  # OwnerUpdateGate + UpdateGateInstaller: вход только владельцу
├── agent_notifications/     # Уведомления рабочих агентов из RabbitMQ: журнал, пересылка владельцу, потребитель
├── ai_tools/                # Инструменты модели: пакет на инструмент, класс — наследник BaseTool
├── chat/
│   ├── actions/
│   │   ├── send_to_agent_action.py   # Текст → AIApplication.process_message → ответ в чат
│   │   ├── system_prompt_builder.py  # data/system_prompt.txt + сегодняшняя дата на каждый запрос
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
├── todoist/                 # TodoistHttpClient (API v1, без close/reopen/delete), TodoistTaskService: дела, подзадачи, ссылки-комментарии
├── conversations/           # Контракт источника переписки: модели, ошибки, Protocol-ы (реализации — gmail, whatsapp)
├── gmail/                   # GmailClient (поиск, чтение, вложения, черновики — без отправки), UntrustedMailFrame
├── whatsapp/                # Источник переписки WhatsApp: платформенные реализации протокола src.conversations
│   └── macos_desktop/       # WhatsApp Desktop на macOS: чтение снимка ChatStorage.sqlite и медиа (host/ — хост-процесс снимка)
├── files/                   # Механика «файл»: WorkFolder, источники (IFileSource; mail/dropbox/chat), ридеры, растр, OverflowFolder, Sweeper
└── voice_recognition/       # HttpTranscriber, NativeTranscriber
scripts/
└── gmail_auth.py            # Получение refresh token Gmail владельца в pass (standalone, uv run)
data/
├── system_prompt.txt        # Системный промпт ассистента; {today}, {now}, {timezone} подставляются на каждый запрос
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

## Инструменты (tools)

Точка регистрации одна — список `tools` в `workers/bot/__main__.py`, он передаётся в `AIApplication`.
`ClaudeSdkProvider` отдаёт их CLI как SDK MCP-сервер `ai-framework-tools`: модель видит `mcp__ai-framework-tools__<name>`.
До v0.9.4 ai_framework дописывал в системный промпт список инструментов голыми именами — модель порой вызывала
голое `wiki_create_page`, CLI отвечал «No such tool available», и бот говорил владельцу, что инструменты недоступны.
С v0.9.4 блок «Available tools» при `ClaudeSdkProvider` идёт с полными именами. `data/checkup_prompt.txt` и
`data/memory_fill_prompt.txt` называют инструменты полными именами; `data/system_prompt.txt` — короткими, а в начале
раздела «Возможности» указание вызывать по полному имени `mcp__ai-framework-tools__<имя>`: оно остаётся до
подтверждения на проде, при правке промпта его не терять. `claude_sdk_live_check` идёт с
коротким промптом-заглушкой, а не с `data/system_prompt.txt`, — поведение настоящего промпта он не проверяет.

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
- `uv run python -m scripts.claude_sdk_live_check bot|checkup` — живой прогон `AIApplication(CLAUDE_SDK)` со
  списком инструментов бота или чекапа на локальных подменах источников (Todoist — `FakeTodoistClient`, в конце
  прогона `bot` в лог идут заведённые задачи и комментарии), вызовы модели настоящие.
  Нативно файл — project settings, а `allowManaged*Only` действует только из managed: запрос разрешения на
  инструмент бота ловится лишь прогоном в образе — `docker build -f deploy/Dockerfile -t <свой тег> .`, затем
  `docker run --rm -e CLAUDE_CODE_OAUTH_TOKEN -v "$PWD/scripts:/app/scripts:ro" -v "$PWD/tests:/app/tests:ro" -v "$PWD/deploy:/app/deploy:ro" --entrypoint python <тег> -m scripts.claude_sdk_live_check bot`

Обновил `claude-agent-sdk` в `uv.lock` — прогони `claude_cli_tools_check`: новый инструмент CLI добавляется в `deny`.
Инструменты вызываются синхронно изнутри event loop провайдера: `asyncio.run` в их коде падает (так `GitCli`
гоняет git своим циклом в отдельном потоке)

### Todoist и Gmail

Регистрируются в `__main__.py` через `workers/bot/todoist_tools_factory.py` и `workers/bot/gmail_tools_factory.py`,
если заданы переменные: `TODOIST_TOKEN` — `find_tasks`, `create_task`, `read_task`, `add_task_link`,
`update_task`; все три `GMAIL_*` — `search_mail`, `read_mail`,
`draft_reply`, `draft_mail` (задана только часть `GMAIL_*` — бот падает на старте). В проде compose требует все четыре.
Список зарегистрированных инструментов пишется в лог на старте строкой `AI tools: …`.

Граница задаётся набором методов, а не промптом:

- **Почта не отправляется.** Инструмента отправки нет, в `GmailClient` нет метода send. `draft_reply` — ответ в
  существующий тред, адресата и тему берёт код из исходного письма; `draft_mail` — черновик нового письма, адресата
  и тему задаёт модель (отправляет владелец из Gmail). Оба принимают `file_ids` — вложения из рабочей папки.
  Scope токена — `gmail.readonly` + `gmail.compose`
- `read_mail` перечисляет вложения с `attachment_id` — это partId части письма (короткий и стабильный), а не
  attachmentId Gmail: `GmailClient.get_attachment` находит часть по partId и качает по свежему attachmentId
- **Задачи не закрываются и не удаляются.** В `TodoistHttpClient` нет close/reopen/delete. `update_task` меняет
  только срок (`clear_due` снимает его как due «no date» с `due_lang` ru — проверено на живом Todoist), дедлайн
  (`clear_deadline` шлёт `deadline_date: null`) и метки — дописывает к текущим, `pa` на чужую задачу не навешивает
- `create_task` — метка `pa` ставится кодом, не моделью. Срок необязателен; `deadline` — внешняя граница
  (`YYYY-MM-DD`), `parent_id` — подзадача. Проект — по имени и только по указанию владельца, без него — Входящие;
  неизвестный проект — ошибка модели без создания задачи, новый проект — только с `create_project`. Метки — `pa` плюс
  названные владельцем
- Дело = задача Todoist с подзадачами, ссылки на источники (вики, Dropbox, письмо, контакт) — отдельными
  комментариями через `add_task_link`; `read_task` отдаёт задачу, подзадачи и комментарии. Поиск дела по названию —
  `find_tasks` («search: <тема>»). Файлов дел в вики нет
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
  `whatsapp:<message>/<attachment>`); нескачанное Desktop — ошибка с просьбой владельцу скачать файл в WhatsApp Desktop

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

## Вики

Слой `src/wiki` — локальная git-копия `obsidian_wiki` (`WIKI_DIR`): первый вызов делает clone по `WIKI_REMOTE_URL`
на пустом каталоге, дальше pull перед чтением; запись — коммит `pa: …` и push в `main` ключом `WIKI_SSH_KEY_PATH`.
Сборка — `build_wiki_tools` в `workers/bot/__main__.py`: один `WikiFactory` на бот, инструменты
`wiki_search` (`WikiSearcher` поверх `WikiReader`), `wiki_read`, `wiki_create_page`, `wiki_append`.
Инструменты памяти (`memory_*`) работают через тот же `WikiFactory` — общий замок на копию.
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
WIKI_DIR=/path/to/obsidian_wiki                 # локальная копия вики; пустой каталог — бот сам сделает clone
WIKI_REMOTE_URL=git@github.com:sumarokov-vp/obsidian_wiki.git
WIKI_SSH_KEY_PATH=/path/to/deploy_key           # необязательная; без неё git берёт ssh-ключи/агент пользователя
DROPBOX_ROOT=/path/to/Dropbox                   # необязательная; без неё инструменты Dropbox не регистрируются
ATTACHMENTS_S3_ENDPOINT=https://fra1.digitaloceanspaces.com   # хранилище вложений (фото, PDF) — DO Spaces
ATTACHMENTS_S3_BUCKET=sumarokov-pa-attachments
ATTACHMENTS_S3_REGION=fra1
ATTACHMENTS_S3_ACCESS_KEY=ключ Spaces
ATTACHMENTS_S3_SECRET_KEY=секрет Spaces
TODOIST_TOKEN=токен                             # необязательная; без неё инструменты Todoist не регистрируются
GMAIL_CLIENT_ID=id OAuth-клиента                # GMAIL_* — все три или ни одной; без них инструменты почты не регистрируются
GMAIL_CLIENT_SECRET=секрет OAuth-клиента
GMAIL_REFRESH_TOKEN=refresh token владельца     # uv run scripts/gmail_auth.py
RABBITMQ_URL=amqp://pa-consumer:пароль@localhost:5672/assistant   # необязательная; без неё уведомления агентов не принимаются
WHATSAPP_MACOS_SNAPSHOT_DIR=~/docker/personal_assistant/whatsapp  # необязательная; снимок WhatsApp Desktop (macOS); без неё инструментов WhatsApp нет
PA_WORK_DIR=/tmp/personal_assistant/files       # необязательная (дефолт — <tempdir>/personal_assistant/files); рабочая папка файлов, уборка через сутки
```

Обязательны на старте бота: `OWNER_TELEGRAM_ID`, `BOT_TOKEN`, `BOT_DB_URL`, `REDIS_URL`, `AI_DB_URL`, `AI_MODEL`, `WIKI_DIR`,
`WIKI_REMOTE_URL`, `ATTACHMENTS_S3_*`. `TODOIST_TOKEN`, `GMAIL_*` и `WHATSAPP_MACOS_SNAPSHOT_DIR` в коде бота необязательны (нет — нет инструментов),
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
- `file_take` (`mail` — `message_id` + `attachment_id` из `read_mail`; `dropbox` — `path` через `DropboxBoundary`, закрытые
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
- `ConversationAttachment.downloaded` — лежит ли файл у источника (WhatsApp Desktop хранит только скачанное);
  `fetch_attachment` нескачанного бросает `AttachmentNotDownloadedError` с подсказкой владельцу. Остальные ошибки —
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
  Скачано — файл есть в `<снимок>/Message/<ZMEDIALOCALPATH>`. Desktop хранит только скачанное:
  нескачанное — `AttachmentNotDownloadedError` «открой чат в WhatsApp Desktop и скачай файл».
  CDN/`ZMEDIAKEY` не используются (решение владельца, в later)
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

## Технологический стек

- Python 3.13+
- bot-framework[all]==0.8.2 — фреймворк для Telegram-ботов
- ai-bot-framework[claude-sdk,s3] (git-тег v0.9.5) — AIApplication, память, ClaudeSdkProvider, вложения в S3, картинки в результате инструмента
- pika — потребитель уведомлений агентов из RabbitMQ
- pypdf, python-docx, openpyxl — текст PDF/DOCX/XLSX; pypdfium2 — скан-PDF в PNG; Pillow — ужать картинку под 5 МБ
- uv — управление зависимостями

## Команды

- Установка зависимостей: `uv sync`
- Запуск бота: `uv run python -m workers.bot`
- Проверки: `uv run ruff check .`, `uv run mypy src workers tests scripts`, `uv run lint-imports`, `uv run pytest`

## Deploy

- Бот работает контейнером в colima на Mac mini (linux/arm64). В образе CLI Claude Code из колеса
  `claude-agent-sdk` со встроенными инструментами, выключенными managed settings (см. выше); git и openssh-client —
  для вики, ключи хоста github.com — из `deploy/ssh/known_hosts` (системный known_hosts); typst и jq нет.
  Деплой — `deploy/up.sh` (скилл `/deploy`), локально, без SSH
- `up.sh` берёт секреты из pass (`assistant/personal_assistant/{bot-token,owner-telegram-id,db,claude-oauth-token,voice-recognition-key,obsidian-wiki-deploy-key,spaces-attachments,todoist-token,gmail-oauth-client,gmail-refresh-token}`,
  `GNUPGHOME=~/docker/personal_assistant/gnupg` — свой GPG-ключ ассистента), собирает из `db` переменную
  `AI_DB_URL` (`options=-csearch_path%3Dai`), разбирает `spaces-attachments` (первая строка — secret key → `ATTACHMENTS_S3_SECRET_KEY`,
  строки `access_key=`, `bucket=`, `region=`, `endpoint=` → остальные `ATTACHMENTS_S3_*`), из `gmail-oauth-client`
(JSON `client_secret_*.json` целиком) достаёт `installed.client_id`/`installed.client_secret` через `python3` → `GMAIL_CLIENT_ID`/`GMAIL_CLIENT_SECRET`,
первые строки `todoist-token` и `gmail-refresh-token` → `TODOIST_TOKEN`, `GMAIL_REFRESH_TOKEN`, и запускает `docker compose -f deploy/compose.yaml up -d --build`.
  Секреты идут переменными окружения, в файлы не пишутся — кроме deploy-ключа вики: ssh читает ключ только из
  файла, `up.sh` кладёт его в `~/docker/personal_assistant/secrets/wiki_deploy_key` (0600, каталог 0700), в
  контейнер он монтируется read-only как `/run/secrets/wiki_deploy_key` (`WIKI_SSH_KEY_PATH`)
- Вики: том `~/docker/personal_assistant/wiki` → `/wiki`, `WIKI_DIR=/wiki/obsidian_wiki`; первый clone на пустом
  томе делает сам бот. `WIKI_REMOTE_URL` — `git@github.com:sumarokov-vp/obsidian_wiki.git` (дефолт в compose/up.sh)
- Схему `ai` в БД `personal_assistant` `up.sh` не создаёт — `CREATE SCHEMA IF NOT EXISTS ai` делается один раз
  руками (`docker exec -u postgres postgres psql -U sumarokov -d personal_assistant`), миграции ai_framework её не создают
- Сеть — внешняя `infra`: `postgres`, `redis` по именам. `network_mode: host` в colima указывал бы на Linux-VM, а не на mac
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
- В контейнере uid 1000; монтируются том вики, ключ вики и Dropbox: сессии CLI живут в `$HOME/.claude` контейнера
  и пропадают с ним. Рабочая папка файлов — `/tmp/personal_assistant/files` контейнера, без тома (`PA_WORK_DIR` в compose
  не задаётся — дефолт кода); проверить: `docker exec personal_assistant_bot ls -la /tmp/personal_assistant/files`
- `docker compose build` без `up.sh` требует заглушки секретов, compose интерполирует `${VAR:?}` и при сборке:
  `OWNER_TELEGRAM_ID=x TODOIST_TOKEN=x GMAIL_CLIENT_ID=x GMAIL_CLIENT_SECRET=x GMAIL_REFRESH_TOKEN=x BOT_TOKEN=x BOT_DB_URL=x AI_DB_URL=x CLAUDE_CODE_OAUTH_TOKEN=x VOICE_RECOGNITION_API_KEY=x PA_DATA_DIR=x WIKI_DEPLOY_KEY_FILE=x ATTACHMENTS_S3_ENDPOINT=x ATTACHMENTS_S3_BUCKET=x ATTACHMENTS_S3_REGION=x ATTACHMENTS_S3_ACCESS_KEY=x ATTACHMENTS_S3_SECRET_KEY=x DROPBOX_DIR=x RABBITMQ_URL=x docker compose -f deploy/compose.yaml build`.
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
