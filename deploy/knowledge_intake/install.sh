#!/usr/bin/env bash
# Установка приёмщика знаний на хост Mac mini: строка crontab и ротация лога newsyslog.
# Идемпотентно: строка с меткой «# knowledge-intake» заменяется, конфиг newsyslog перезаписывается.
# Сам воркер живёт в контейнере personal_assistant_bot — его выкатывает deploy/up.sh.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
MARK="# knowledge-intake"
LOG_DIR="$HOME/Library/Logs/personal_assistant"
NEWSYSLOG_TARGET="/etc/newsyslog.d/personal-assistant-knowledge-intake.conf"

mkdir -p "$LOG_DIR"

CRON_LINE="$(grep -v '^#' "$HERE/crontab" | grep -F "$MARK")"
{ crontab -l 2>/dev/null | grep -vF "$MARK" || true; echo "$CRON_LINE"; } | crontab -
echo "install.sh: crontab — $(crontab -l | grep -cF "$MARK") строка knowledge-intake"

if ! cmp -s "$HERE/newsyslog.conf" "$NEWSYSLOG_TARGET" 2>/dev/null; then
    sudo install -m 644 -o root -g wheel "$HERE/newsyslog.conf" "$NEWSYSLOG_TARGET"
    echo "install.sh: $NEWSYSLOG_TARGET обновлён"
fi
sudo newsyslog -n -f "$NEWSYSLOG_TARGET" > /dev/null
