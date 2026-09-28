#!/usr/bin/env bash
# Сборка и запуск бота в colima. Секреты берутся из pass (ветка ассистента, свой GPG-ключ)
# и живут только в окружении этого процесса — в файлы не пишутся. Исключение — deploy-ключ
# вики: ssh берёт ключ только из файла, он кладётся 0600 в ~/docker/personal_assistant/secrets.
set -euo pipefail

export GNUPGHOME="$HOME/docker/personal_assistant/gnupg"

PASS_ROOT="assistant/personal_assistant"
PA_DATA_DIR="$HOME/docker/personal_assistant"
SECRETS_DIR="$PA_DATA_DIR/secrets"
DROPBOX_DIR="$HOME/Dropbox"
EMPTY_DIR="$PA_DATA_DIR/empty"
WIKI_DEPLOY_KEY_FILE="$SECRETS_DIR/wiki_deploy_key"

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

# Deploy-ключ вики: ssh читает ключ только из файла. Файл 0600 в каталоге 0700 вне репо и вне
# тома вики, в контейнер монтируется только на чтение. Пишется целиком (ключ многострочный),
# через umask — без окна, когда файл уже есть, а права ещё широкие.
mkdir -p "$PA_DATA_DIR/wiki"
( umask 077 && mkdir -p "$SECRETS_DIR" && pass show "$PASS_ROOT/obsidian-wiki-deploy-key" > "$WIKI_DEPLOY_KEY_FILE.tmp" )
chmod 700 "$SECRETS_DIR"
chmod 600 "$WIKI_DEPLOY_KEY_FILE.tmp"
mv -f "$WIKI_DEPLOY_KEY_FILE.tmp" "$WIKI_DEPLOY_KEY_FILE"

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

# Каталог агентов: корпоративный слой (git-клон репозитория компании, когда он появится) и
# личный. Монтируются только на чтение; без каталогов docker создал бы их сам от root
mkdir -p "$PA_DATA_DIR/corporate_agents" "$PA_DATA_DIR/personal_agents"

export BOT_TOKEN OWNER_TELEGRAM_ID BOT_DB_URL AI_DB_URL CLAUDE_CODE_OAUTH_TOKEN VOICE_RECOGNITION_API_KEY AI_MODEL \
    CLAUDE_CODE_EFFORT_LEVEL \
    WIKI_REMOTE_URL PA_DATA_DIR WIKI_DEPLOY_KEY_FILE DROPBOX_DIR \
    ATTACHMENTS_S3_ENDPOINT ATTACHMENTS_S3_BUCKET ATTACHMENTS_S3_REGION \
    ATTACHMENTS_S3_ACCESS_KEY ATTACHMENTS_S3_SECRET_KEY \
    TODOIST_TOKEN GMAIL_CLIENT_ID GMAIL_CLIENT_SECRET GMAIL_REFRESH_TOKEN \
    RABBITMQ_URL

docker compose -f deploy/compose.yaml up -d --build
