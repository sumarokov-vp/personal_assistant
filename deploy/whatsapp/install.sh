#!/usr/bin/env bash
# Установка launchd-агента снимка WhatsApp (идемпотентно, вызывается из deploy/up.sh).
#
# Собирает whatsapp_snapshot.c в ~/docker/personal_assistant/bin/whatsapp_snapshot и
# держит агента com.sumarokov.personal-assistant.whatsapp-snapshot загруженным в GUI-сессии.
# «Полный доступ к диску» macOS выдаётся этому файлу вручную. Разрешение привязано к подписи
# файла, а подпись у пересобранного файла другая — поэтому файл пересобирается только при
# изменении исходника; после пересборки доступ выдаётся заново.
set -euo pipefail

LABEL="com.sumarokov.personal-assistant.whatsapp-snapshot"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_FILE="$SOURCE_DIR/whatsapp_snapshot.c"
PLIST_TEMPLATE="$SOURCE_DIR/$LABEL.plist"
PA_DATA_DIR="$HOME/docker/personal_assistant"
BIN_DIR="$PA_DATA_DIR/bin"
BINARY="$BIN_DIR/whatsapp_snapshot"
BINARY_SOURCE_HASH="$BINARY.source-sha256"
SNAPSHOT_DIR="$PA_DATA_DIR/whatsapp"
LOG_DIR="$HOME/Library/Logs/personal_assistant"
LOG_FILE="$LOG_DIR/whatsapp_snapshot.log"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
BUILD_FLAGS="-O2 -Wall -Wextra -Wpedantic -Werror"
DOMAIN="gui/$(id -u)"

mkdir -p "$BIN_DIR" "$SNAPSHOT_DIR" "$LOG_DIR" "$(dirname "$PLIST")"

source_hash="$( { cat "$SOURCE_FILE"; echo "$BUILD_FLAGS"; } | shasum -a 256 | awk '{print $1}')"
binary_rebuilt=0
if [ ! -x "$BINARY" ] || [ "$(cat "$BINARY_SOURCE_HASH" 2>/dev/null)" != "$source_hash" ]; then
    # shellcheck disable=SC2086  # флаги сборки — список слов
    cc $BUILD_FLAGS -o "$BINARY.tmp" "$SOURCE_FILE" -lsqlite3
    mv -f "$BINARY.tmp" "$BINARY"
    echo "$source_hash" > "$BINARY_SOURCE_HASH"
    binary_rebuilt=1
fi

plist_content="$(sed -e "s#@BINARY@#$BINARY#g" -e "s#@LOG_FILE@#$LOG_FILE#g" "$PLIST_TEMPLATE")"
plist_changed=0
if [ ! -f "$PLIST" ] || [ "$(cat "$PLIST")" != "$plist_content" ]; then
    printf '%s\n' "$plist_content" > "$PLIST.tmp"
    plutil -lint "$PLIST.tmp" > /dev/null
    mv -f "$PLIST.tmp" "$PLIST"
    plist_changed=1
fi

if launchctl print "$DOMAIN/$LABEL" > /dev/null 2>&1; then
    if [ "$plist_changed" = 1 ]; then
        launchctl bootout "$DOMAIN/$LABEL"
        launchctl bootstrap "$DOMAIN" "$PLIST"
    elif [ "$binary_rebuilt" = 1 ]; then
        launchctl kickstart -k "$DOMAIN/$LABEL"
    fi
else
    launchctl bootstrap "$DOMAIN" "$PLIST"
fi

if [ "$binary_rebuilt" = 1 ]; then
    echo "whatsapp_snapshot: файл собран заново — выдать ему «Полный доступ к диску»: $BINARY" >&2
fi
