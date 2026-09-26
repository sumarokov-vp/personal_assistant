#!/usr/bin/env bash
# Сборка и запуск бота в colima. Секреты берутся из pass (ветка ассистента, свой GPG-ключ)
# и живут только в окружении этого процесса — в файлы не пишутся. Исключение — deploy-ключ
# вики: ssh берёт ключ только из файла, он кладётся 0600 в ~/docker/personal_assistant/secrets.
set -euo pipefail

export GNUPGHOME="$HOME/docker/personal_assistant/gnupg"

PASS_ROOT="assistant/personal_assistant"
PA_DATA_DIR="$HOME/docker/personal_assistant"
SECRETS_DIR="$PA_DATA_DIR/secrets"
WIKI_DEPLOY_KEY_FILE="$SECRETS_DIR/wiki_deploy_key"

cd "$(dirname "$0")/.."

pass_first_line() {
    pass show "$1" | head -n 1
}

# Поле «key=value» из строк записи pass ниже первой (первая — секрет)
pass_field() {
    pass show "$1" | tail -n +2 | sed -n "s/^$2=//p" | awk "NR == 1"
}

require_value() {
    if [ -z "$2" ]; then
        echo "up.sh: в pass нет значения для $1" >&2
        exit 1
    fi
}

BOT_TOKEN="$(pass_first_line "$PASS_ROOT/bot-token")"
BOT_DB_URL="$(pass_first_line "$PASS_ROOT/db")"
AI_DB_URL="${BOT_DB_URL}&options=-csearch_path%3Dai"
CLAUDE_CODE_OAUTH_TOKEN="$(pass_first_line "$PASS_ROOT/claude-oauth-token")"
VOICE_RECOGNITION_API_KEY="$(pass_first_line "$PASS_ROOT/voice-recognition-key")"
AI_MODEL="${AI_MODEL:-claude-sonnet-4-5}"
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

# Deploy-ключ вики: ssh читает ключ только из файла. Файл 0600 в каталоге 0700 вне репо и вне
# тома вики, в контейнер монтируется только на чтение. Пишется целиком (ключ многострочный),
# через umask — без окна, когда файл уже есть, а права ещё широкие.
mkdir -p "$PA_DATA_DIR/wiki"
( umask 077 && mkdir -p "$SECRETS_DIR" && pass show "$PASS_ROOT/obsidian-wiki-deploy-key" > "$WIKI_DEPLOY_KEY_FILE.tmp" )
chmod 700 "$SECRETS_DIR"
chmod 600 "$WIKI_DEPLOY_KEY_FILE.tmp"
mv -f "$WIKI_DEPLOY_KEY_FILE.tmp" "$WIKI_DEPLOY_KEY_FILE"

export BOT_TOKEN BOT_DB_URL AI_DB_URL CLAUDE_CODE_OAUTH_TOKEN VOICE_RECOGNITION_API_KEY AI_MODEL \
    WIKI_REMOTE_URL PA_DATA_DIR WIKI_DEPLOY_KEY_FILE \
    ATTACHMENTS_S3_ENDPOINT ATTACHMENTS_S3_BUCKET ATTACHMENTS_S3_REGION \
    ATTACHMENTS_S3_ACCESS_KEY ATTACHMENTS_S3_SECRET_KEY

docker compose -f deploy/compose.yaml up -d --build
