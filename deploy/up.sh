#!/usr/bin/env bash
# Сборка и запуск бота в colima. Секреты берутся из pass (ветка ассистента, свой GPG-ключ)
# и живут только в окружении этого процесса — в файлы не пишутся. Исключения — deploy-ключ
# вики (ssh берёт ключ только из файла) и сессия Telegram владельца: они кладутся 0600 в
# ~/docker/personal_assistant/secrets.
set -euo pipefail

export GNUPGHOME="$HOME/docker/personal_assistant/gnupg"
# Новую запись в assistant/ шифруют публичные ключи всех получателей — они в связке оператора,
# а не в связке ассистента (там только секретная половина ключа ассистента)
OPERATOR_GNUPGHOME="$HOME/.config/gnupg"

PASS_ROOT="assistant/personal_assistant"
PA_DATA_DIR="$HOME/docker/personal_assistant"
SECRETS_DIR="$PA_DATA_DIR/secrets"
DROPBOX_DIR="$HOME/Dropbox"
EMPTY_DIR="$PA_DATA_DIR/empty"
ASSISTANT_DIRECTORY_FILE="$PA_DATA_DIR/directory.yaml"
WIKI_DEPLOY_KEY_FILE="$SECRETS_DIR/wiki_deploy_key"
TELEGRAM_SECRETS_DIR="$SECRETS_DIR/telegram"
TELEGRAM_USER_SECRETS_FILE="$TELEGRAM_SECRETS_DIR/telegram_user"
MCP_KEY_ENTRY="assistant/personal_assistant/mcp-key"
MCP_JOURNAL_DIR="$PA_DATA_DIR/mcp"

cd "$(dirname "$0")/.."

pass_first_line() {
    pass show "$1" | head -n 1
}

# Поле «key=value» из строк записи pass ниже первой (первая — секрет)
pass_field() {
    pass show "$1" | tail -n +2 | sed -n "s/^$2=//p" | awk "NR == 1"
}

# Поле installed.<имя> из OAuth-клиента Google: запись pass — JSON client_secret_*.json целиком.
# Значение идёт через stdin, в аргументы процесса секрет не попадает
oauth_client_field() {
    pass show "$1" | python3 -c 'import json, sys; print(json.load(sys.stdin)["installed"][sys.argv[1]])' "$2"
}

# Поле «key=value» из любой строки записи pass (у записи без секрета в первой строке)
pass_any_field() {
    pass show "$1" | sed -n "s/^$2=//p" | awk "NR == 1"
}

# Есть ли запись в pass — по файлу хранилища, без расшифровки
pass_entry_exists() {
    [ -f "${PASSWORD_STORE_DIR:-$HOME/.password-store}/$1.gpg" ]
}

require_value() {
    if [ -z "$2" ]; then
        echo "up.sh: в pass нет значения для $1" >&2
        exit 1
    fi
}

BOT_TOKEN="$(pass_first_line "$PASS_ROOT/bot-token")"
# Бот слышит только владельца: без его Telegram ID выкат останавливается здесь
OWNER_TELEGRAM_ID="$(pass_first_line "$PASS_ROOT/owner-telegram-id")"
require_value "$PASS_ROOT/owner-telegram-id" "$OWNER_TELEGRAM_ID"
BOT_DB_URL="$(pass_first_line "$PASS_ROOT/db")"
AI_DB_URL="${BOT_DB_URL}&options=-csearch_path%3Dai"
CLAUDE_CODE_OAUTH_TOKEN="$(pass_first_line "$PASS_ROOT/claude-oauth-token")"
VOICE_RECOGNITION_API_KEY="$(pass_first_line "$PASS_ROOT/voice-recognition-key")"
AI_MODEL="${AI_MODEL:-claude-sonnet-5}"
# Effort CLI Claude Code (low|medium|high|xhigh): low выключает thinking, ход быстрее. CLI читает env сам
CLAUDE_CODE_EFFORT_LEVEL="${CLAUDE_CODE_EFFORT_LEVEL:-low}"
WIKI_REMOTE_URL="${WIKI_REMOTE_URL:-git@github.com:sumarokov-vp/obsidian_wiki.git}"

# Вложения (фото, PDF) — DO Spaces. Запись spaces-attachments: первая строка — secret key,
# ниже строки access_key=, bucket=, region=, endpoint=
SPACES_ENTRY="$PASS_ROOT/spaces-attachments"
ATTACHMENTS_S3_SECRET_KEY="$(pass_first_line "$SPACES_ENTRY")"
ATTACHMENTS_S3_ACCESS_KEY="$(pass_field "$SPACES_ENTRY" access_key)"
ATTACHMENTS_S3_BUCKET="$(pass_field "$SPACES_ENTRY" bucket)"
ATTACHMENTS_S3_REGION="$(pass_field "$SPACES_ENTRY" region)"
ATTACHMENTS_S3_ENDPOINT="$(pass_field "$SPACES_ENTRY" endpoint)"
require_value "$SPACES_ENTRY (secret)" "$ATTACHMENTS_S3_SECRET_KEY"
require_value "$SPACES_ENTRY access_key" "$ATTACHMENTS_S3_ACCESS_KEY"
require_value "$SPACES_ENTRY bucket" "$ATTACHMENTS_S3_BUCKET"
require_value "$SPACES_ENTRY region" "$ATTACHMENTS_S3_REGION"
require_value "$SPACES_ENTRY endpoint" "$ATTACHMENTS_S3_ENDPOINT"

# Todoist и Gmail. Refresh token Gmail владелец кладёт в pass скриптом scripts/gmail_auth.py
# (uv run scripts/gmail_auth.py); пока записи нет, выкат останавливается здесь
TODOIST_TOKEN="$(pass_first_line "$PASS_ROOT/todoist-token")"
GMAIL_CLIENT_ID="$(oauth_client_field "$PASS_ROOT/gmail-oauth-client" client_id)"
GMAIL_CLIENT_SECRET="$(oauth_client_field "$PASS_ROOT/gmail-oauth-client" client_secret)"
GMAIL_REFRESH_TOKEN="$(pass_first_line "$PASS_ROOT/gmail-refresh-token")"
require_value "$PASS_ROOT/todoist-token" "$TODOIST_TOKEN"
require_value "$PASS_ROOT/gmail-oauth-client installed.client_id" "$GMAIL_CLIENT_ID"
require_value "$PASS_ROOT/gmail-oauth-client installed.client_secret" "$GMAIL_CLIENT_SECRET"
require_value "$PASS_ROOT/gmail-refresh-token" "$GMAIL_REFRESH_TOKEN"

# Уведомления рабочих агентов: URL учётки pa-consumer (только чтение pa.notifications в vhost
# assistant). Запись и учётку заводит deploy/rabbitmq/setup.sh
RABBITMQ_URL="$(pass_first_line "$PASS_ROOT/rabbitmq")"
require_value "$PASS_ROOT/rabbitmq" "$RABBITMQ_URL"

# Сервис кейсов assistant_cases (соседний контейнер в сети infra): ключ API ассистента. Его же строка
# «user:ключ» лежит в записи API_KEYS сервиса кейсов — ключ определяет, чьи это кейсы
CASES_API_KEY="$(pass_first_line "$PASS_ROOT/cases-api-key")"
require_value "$PASS_ROOT/cases-api-key" "$CASES_API_KEY"
CASES_API_URL="${CASES_API_URL:-http://assistant_cases:8000}"

# Сервис расписаний assistant_scheduler (соседний контейнер в сети infra). SCHEDULER_API_KEY — ключ
# пользователя sumarokov из записи api-keys сервиса (инструменты schedule_*); SCHEDULER_AMQP_URL — учётка
# schedule-sumarokov (только чтение schedule.sumarokov в vhost assistant), её заводит топология
# assistant_scheduler (deploy/rabbitmq/setup.sh той репы). Адрес и очередь — в compose.yaml
SCHEDULER_API_KEY="$(pass_first_line "$PASS_ROOT/scheduler-api-key")"
require_value "$PASS_ROOT/scheduler-api-key" "$SCHEDULER_API_KEY"
SCHEDULER_AMQP_URL="$(pass_first_line "$PASS_ROOT/scheduler-amqp")"
require_value "$PASS_ROOT/scheduler-amqp" "$SCHEDULER_AMQP_URL"

# Почта ассистентов: URL учётки assistant-sumarokov в vhost assistants.sumarokov (пишет в
# exchange assistant-mail, читает только inbox.sumarokov). Запись, ящик и учётку заводит
# deploy/rabbitmq/assistants.sh add-assistant sumarokov
ASSISTANT_MAIL_URL="$(pass_first_line "$PASS_ROOT/assistant-mail")"
require_value "$PASS_ROOT/assistant-mail" "$ASSISTANT_MAIL_URL"
ASSISTANT_KEY="${ASSISTANT_KEY:-sumarokov}"

# Справочник коллег (ключ ассистента → имя, editor) — на хосте, в контейнер только на чтение.
# Нет файла — заготовка с одной записью владельца; существующий не трогается
if [ ! -f "$ASSISTANT_DIRECTORY_FILE" ]; then
    mkdir -p "$PA_DATA_DIR"
    cat > "$ASSISTANT_DIRECTORY_FILE" <<'YAML'
# Справочник коллег для почты ассистентов: ключ ассистента → имя сотрудника и флаг editor
# (редактор общего агента — получает замечания). Ключ — тот же, что в assistant-<ключ> брокера.
sumarokov:
  name: Сумароков Владимир
  editor: true
YAML
    echo "up.sh: справочник коллег создан — $ASSISTANT_DIRECTORY_FILE"
fi

# Deploy-ключ вики: ssh читает ключ только из файла. Файл 0600 в каталоге 0700 вне репо и вне
# тома вики, в контейнер монтируется только на чтение. Пишется целиком (ключ многострочный),
# через umask — без окна, когда файл уже есть, а права ещё широкие.
mkdir -p "$PA_DATA_DIR/wiki"
( umask 077 && mkdir -p "$SECRETS_DIR" && pass show "$PASS_ROOT/obsidian-wiki-deploy-key" > "$WIKI_DEPLOY_KEY_FILE.tmp" )
chmod 700 "$SECRETS_DIR"
chmod 600 "$WIKI_DEPLOY_KEY_FILE.tmp"
mv -f "$WIKI_DEPLOY_KEY_FILE.tmp" "$WIKI_DEPLOY_KEY_FILE"

# Telegram владельца (MTProto, Telethon): сессия StringSession — ключ от всего аккаунта. Файл
# секретов из трёх строк session=, api_id=, api_hash= (формат держит src/telegram_user/repos/
# telegram_secrets_file.py) кладётся 0600 в каталог 0700 и монтируется в контейнер только на
# чтение — каталогом, чтобы отсутствие файла не превращалось в пустой каталог на его месте.
# Сессия — pass telegram-user (одна строка), приложение my.telegram.org — telegram-app (строки
# api_id=, api_hash=). Нет записи telegram-user — владелец ещё не входил (scripts/telegram_login.py):
# файла нет, бот стартует без инструментов Telegram, выкат идёт дальше. Значения не попадают ни в
# аргументы процессов (printf — встроенная команда bash), ни в вывод.
( umask 077 && mkdir -p "$TELEGRAM_SECRETS_DIR" )
chmod 700 "$TELEGRAM_SECRETS_DIR"
if pass_entry_exists "$PASS_ROOT/telegram-user"; then
    TELEGRAM_SESSION="$(pass_first_line "$PASS_ROOT/telegram-user")"
    TELEGRAM_API_ID="$(pass_any_field "$PASS_ROOT/telegram-app" api_id)"
    TELEGRAM_API_HASH="$(pass_any_field "$PASS_ROOT/telegram-app" api_hash)"
    require_value "$PASS_ROOT/telegram-user" "$TELEGRAM_SESSION"
    require_value "$PASS_ROOT/telegram-app api_id" "$TELEGRAM_API_ID"
    require_value "$PASS_ROOT/telegram-app api_hash" "$TELEGRAM_API_HASH"
    (
        umask 077
        printf 'session=%s\napi_id=%s\napi_hash=%s\n' \
            "$TELEGRAM_SESSION" "$TELEGRAM_API_ID" "$TELEGRAM_API_HASH" \
            > "$TELEGRAM_USER_SECRETS_FILE.tmp"
    )
    unset TELEGRAM_SESSION TELEGRAM_API_ID TELEGRAM_API_HASH
    chmod 600 "$TELEGRAM_USER_SECRETS_FILE.tmp"
    mv -f "$TELEGRAM_USER_SECRETS_FILE.tmp" "$TELEGRAM_USER_SECRETS_FILE"
else
    # Запись убрали из pass — сессия не должна пережить её в контейнере
    rm -f "$TELEGRAM_USER_SECRETS_FILE" "$TELEGRAM_USER_SECRETS_FILE.tmp"
    echo "up.sh: в pass нет $PASS_ROOT/telegram-user — бот стартует без Telegram владельца"
fi

# Dropbox: том ~/Dropbox, закрытые папки перекрываются пустым каталогом только на чтение
# (compose.yaml). Заглушка обязана быть пустой — иначе её содержимое окажется на месте Vault.
if [ ! -d "$DROPBOX_DIR" ]; then
    echo "up.sh: нет $DROPBOX_DIR — Dropbox (Maestral) на этой машине не настроен" >&2
    exit 1
fi
mkdir -p "$EMPTY_DIR"
if [ -n "$(ls -A "$EMPTY_DIR")" ]; then
    echo "up.sh: заглушка $EMPTY_DIR не пуста — разберись, что туда попало" >&2
    exit 1
fi

# Снимок WhatsApp: launchd-агент хоста копирует базу и медиа WhatsApp Desktop в
# $PA_DATA_DIR/whatsapp. VM colima к папке WhatsApp не обращается никогда — только к снимку
src/whatsapp/macos_desktop/host/install.sh

# WhatsApp Web: хостовый сервис на Mac mini (Chromium/Playwright, launchd-агент
# com.sumarokov.personal-assistant.whatsapp-web) — запасной путь бота за документами, которые
# WhatsApp уже удалил с CDN. install.sh сам заводит pass-запись с ключом и номером (первый
# запуск) и учётку RabbitMQ agent-whatsapp-web; здесь берём только ключ, чтобы отдать боту.
hosts/whatsapp_web/install.sh
WHATSAPP_WEB_URL="http://host.docker.internal:18790"
WHATSAPP_WEB_TOKEN="$(pass_first_line "$PASS_ROOT/whatsapp-web")"

# Ядро MCP (сервис mcp в compose.yaml): статический ключ волны 0 — Authorization: Bearer <ключ>.
# Нет записи mcp-key — заводится здесь (openssl rand, как hosts/whatsapp_web/install.sh); значение
# идёт через pipe, ни в аргументы процессов, ни в вывод не попадает. Каталог журнала — на хосте,
# переживает пересборку контейнера
if ! pass_entry_exists "$MCP_KEY_ENTRY"; then
    openssl rand -hex 32 | GNUPGHOME="$OPERATOR_GNUPGHOME" pass insert --multiline "$MCP_KEY_ENTRY" > /dev/null
    echo "up.sh: pass $MCP_KEY_ENTRY создана"
fi
MCP_STATIC_KEY="$(pass_first_line "$MCP_KEY_ENTRY")"
require_value "$MCP_KEY_ENTRY" "$MCP_STATIC_KEY"
MCP_ALLOWED_PROJECTS="${MCP_ALLOWED_PROJECTS:-assistant}"
mkdir -p "$MCP_JOURNAL_DIR"

# Приёмщик знаний (workers.knowledge_intake; cron хоста зовёт docker exec в контейнер бота —
# deploy/knowledge_intake/install.sh). Ящик — pass knowledge-mailbox: первая строка пароль, ниже
# user=, host=. Deploy-ключ claude-toolkit с записью и список допуска — файлы 0600 в каталоге 0700
# $SECRETS_DIR/knowledge, в контейнер каталогом только на чтение. Допуск — адреса строк email:
# реестра vault:MineRadioSystems/registry/employees.yaml (волт читается ключами оператора, папка
# закрывается сразу после чтения). Нет записи, ключа или реестра — выкат останавливается
KNOWLEDGE_MAILBOX_ENTRY="$PASS_ROOT/knowledge-mailbox"
KNOWLEDGE_IMAP_PASSWORD="$(pass_first_line "$KNOWLEDGE_MAILBOX_ENTRY")"
KNOWLEDGE_IMAP_USER="$(pass_field "$KNOWLEDGE_MAILBOX_ENTRY" user)"
KNOWLEDGE_IMAP_HOST="$(pass_field "$KNOWLEDGE_MAILBOX_ENTRY" host)"
require_value "$KNOWLEDGE_MAILBOX_ENTRY (password)" "$KNOWLEDGE_IMAP_PASSWORD"
require_value "$KNOWLEDGE_MAILBOX_ENTRY user" "$KNOWLEDGE_IMAP_USER"
require_value "$KNOWLEDGE_MAILBOX_ENTRY host" "$KNOWLEDGE_IMAP_HOST"
KNOWLEDGE_SECRETS_DIR="$SECRETS_DIR/knowledge"
KNOWLEDGE_DEPLOY_KEY_FILE="$KNOWLEDGE_SECRETS_DIR/claude_toolkit_deploy_key"
KNOWLEDGE_ALLOWLIST_FILE="$KNOWLEDGE_SECRETS_DIR/allowlist"
KNOWLEDGE_REGISTRY="vault:MineRadioSystems/registry"
( umask 077 && mkdir -p "$KNOWLEDGE_SECRETS_DIR" )
chmod 700 "$KNOWLEDGE_SECRETS_DIR"
( umask 077 && pass show "$PASS_ROOT/claude-toolkit-deploy-key" > "$KNOWLEDGE_DEPLOY_KEY_FILE.tmp" )
chmod 600 "$KNOWLEDGE_DEPLOY_KEY_FILE.tmp"
mv -f "$KNOWLEDGE_DEPLOY_KEY_FILE.tmp" "$KNOWLEDGE_DEPLOY_KEY_FILE"
trap 'GNUPGHOME="$OPERATOR_GNUPGHOME" vault close "$KNOWLEDGE_REGISTRY" > /dev/null || true' EXIT
KNOWLEDGE_REGISTRY_DIR="$(GNUPGHOME="$OPERATOR_GNUPGHOME" vault open "$KNOWLEDGE_REGISTRY")"
(
    umask 077
    sed -n -E "s/^[[:space:]-]*email:[[:space:]]*[\"']?([^\"'[:space:]#]+).*$/\1/p" \
        "$KNOWLEDGE_REGISTRY_DIR/employees.yaml" | tr '[:upper:]' '[:lower:]' | sort -u \
        > "$KNOWLEDGE_ALLOWLIST_FILE.tmp"
)
GNUPGHOME="$OPERATOR_GNUPGHOME" vault close "$KNOWLEDGE_REGISTRY" > /dev/null
trap - EXIT
if [ ! -s "$KNOWLEDGE_ALLOWLIST_FILE.tmp" ]; then
    rm -f "$KNOWLEDGE_ALLOWLIST_FILE.tmp"
    echo "up.sh: в $KNOWLEDGE_REGISTRY/employees.yaml нет ни одного email" >&2
    exit 1
fi
chmod 600 "$KNOWLEDGE_ALLOWLIST_FILE.tmp"
mv -f "$KNOWLEDGE_ALLOWLIST_FILE.tmp" "$KNOWLEDGE_ALLOWLIST_FILE"
echo "up.sh: допуск приёмщика — $(wc -l < "$KNOWLEDGE_ALLOWLIST_FILE" | tr -d ' ') адресов"

export BOT_TOKEN OWNER_TELEGRAM_ID BOT_DB_URL AI_DB_URL CLAUDE_CODE_OAUTH_TOKEN VOICE_RECOGNITION_API_KEY AI_MODEL \
    CLAUDE_CODE_EFFORT_LEVEL \
    WIKI_REMOTE_URL PA_DATA_DIR WIKI_DEPLOY_KEY_FILE DROPBOX_DIR \
    ATTACHMENTS_S3_ENDPOINT ATTACHMENTS_S3_BUCKET ATTACHMENTS_S3_REGION \
    ATTACHMENTS_S3_ACCESS_KEY ATTACHMENTS_S3_SECRET_KEY \
    TODOIST_TOKEN GMAIL_CLIENT_ID GMAIL_CLIENT_SECRET GMAIL_REFRESH_TOKEN \
    RABBITMQ_URL CASES_API_URL CASES_API_KEY \
    SCHEDULER_API_KEY SCHEDULER_AMQP_URL \
    ASSISTANT_MAIL_URL ASSISTANT_KEY ASSISTANT_DIRECTORY_FILE \
    WHATSAPP_WEB_URL WHATSAPP_WEB_TOKEN \
    TELEGRAM_SECRETS_DIR \
    MCP_STATIC_KEY MCP_ALLOWED_PROJECTS \
    KNOWLEDGE_IMAP_HOST KNOWLEDGE_IMAP_USER KNOWLEDGE_IMAP_PASSWORD KNOWLEDGE_SECRETS_DIR

docker compose -f deploy/compose.yaml up -d --build
