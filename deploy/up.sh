#!/usr/bin/env bash
# Сборка и запуск бота в colima. Секреты берутся из pass и живут только в окружении этого процесса.
set -euo pipefail

export GNUPGHOME="${GNUPGHOME:-$HOME/.config/gnupg}"

PASS_ROOT="work/projects/sumarokov/pa/personal_assistant"
VOICE_KEYS_ENTRY="work/projects/internal/infrastructure/voice_recognition/api-keys"
VOICE_KEY_NAME="personal_assistant"
CLAUDE_HOME="$HOME/docker/personal_assistant/claude-home"

cd "$(dirname "$0")/.."

pass_first_line() {
    pass show "$1" | head -n 1
}

voice_recognition_key() {
    local pairs pair
    IFS=',' read -ra pairs <<< "$(pass_first_line "$VOICE_KEYS_ENTRY")"
    for pair in "${pairs[@]}"; do
        if [[ "${pair%%:*}" == "$VOICE_KEY_NAME" ]]; then
            printf '%s' "${pair#*:}"
            return 0
        fi
    done
    echo "В $VOICE_KEYS_ENTRY нет ключа для $VOICE_KEY_NAME" >&2
    return 1
}

BOT_TOKEN="$(pass_first_line "$PASS_ROOT/bot-token")"
BOT_DB_URL="$(pass_first_line "$PASS_ROOT/db")"
CLAUDE_CODE_OAUTH_TOKEN="$(pass_first_line "$PASS_ROOT/claude-oauth-token")"
VOICE_RECOGNITION_API_KEY="$(voice_recognition_key)"
export BOT_TOKEN BOT_DB_URL CLAUDE_CODE_OAUTH_TOKEN VOICE_RECOGNITION_API_KEY

mkdir -p "$CLAUDE_HOME" workspace

docker compose -f deploy/compose.yaml up -d --build
