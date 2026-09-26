#!/usr/bin/env bash
# Сборка и запуск бота в colima. Секреты берутся из pass (ветка ассистента, свой GPG-ключ)
# и живут только в окружении этого процесса — в файлы не пишутся.
set -euo pipefail

export GNUPGHOME="$HOME/docker/personal_assistant/gnupg"

PASS_ROOT="assistant/personal_assistant"

cd "$(dirname "$0")/.."

pass_first_line() {
    pass show "$1" | head -n 1
}

BOT_TOKEN="$(pass_first_line "$PASS_ROOT/bot-token")"
BOT_DB_URL="$(pass_first_line "$PASS_ROOT/db")"
AI_DB_URL="${BOT_DB_URL}&options=-csearch_path%3Dai"
ANTHROPIC_API_KEY="$(pass_first_line "$PASS_ROOT/anthropic-api-key")"
VOICE_RECOGNITION_API_KEY="$(pass_first_line "$PASS_ROOT/voice-recognition-key")"
AI_MODEL="${AI_MODEL:-claude-sonnet-4-5}"
export BOT_TOKEN BOT_DB_URL AI_DB_URL ANTHROPIC_API_KEY VOICE_RECOGNITION_API_KEY AI_MODEL

docker compose -f deploy/compose.yaml up -d --build
