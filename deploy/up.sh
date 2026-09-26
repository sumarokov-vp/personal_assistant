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

BOT_TOKEN="$(pass_first_line "$PASS_ROOT/bot-token")"
BOT_DB_URL="$(pass_first_line "$PASS_ROOT/db")"
AI_DB_URL="${BOT_DB_URL}&options=-csearch_path%3Dai"
CLAUDE_CODE_OAUTH_TOKEN="$(pass_first_line "$PASS_ROOT/claude-oauth-token")"
VOICE_RECOGNITION_API_KEY="$(pass_first_line "$PASS_ROOT/voice-recognition-key")"
AI_MODEL="${AI_MODEL:-claude-sonnet-4-5}"
WIKI_REMOTE_URL="${WIKI_REMOTE_URL:-git@github.com:sumarokov-vp/obsidian_wiki.git}"

# Deploy-ключ вики: ssh читает ключ только из файла. Файл 0600 в каталоге 0700 вне репо и вне
# тома вики, в контейнер монтируется только на чтение. Пишется целиком (ключ многострочный),
# через umask — без окна, когда файл уже есть, а права ещё широкие.
mkdir -p "$PA_DATA_DIR/wiki"
( umask 077 && mkdir -p "$SECRETS_DIR" && pass show "$PASS_ROOT/obsidian-wiki-deploy-key" > "$WIKI_DEPLOY_KEY_FILE.tmp" )
chmod 700 "$SECRETS_DIR"
chmod 600 "$WIKI_DEPLOY_KEY_FILE.tmp"
mv -f "$WIKI_DEPLOY_KEY_FILE.tmp" "$WIKI_DEPLOY_KEY_FILE"

export BOT_TOKEN BOT_DB_URL AI_DB_URL CLAUDE_CODE_OAUTH_TOKEN VOICE_RECOGNITION_API_KEY AI_MODEL \
    WIKI_REMOTE_URL PA_DATA_DIR WIKI_DEPLOY_KEY_FILE

docker compose -f deploy/compose.yaml up -d --build
