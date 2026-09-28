#!/usr/bin/env bash
# Установка launchd-агента снимка WhatsApp (идемпотентно, вызывается из deploy/up.sh).
#
# Собирает whatsapp_snapshot.c в бандл ~/docker/personal_assistant/bin/WhatsAppSnapshot.app
# (Contents/MacOS/whatsapp_snapshot, Info.plist с CFBundleIdentifier = метка агента) и держит
# агента com.sumarokov.personal-assistant.whatsapp-snapshot загруженным в GUI-сессии.
# Бандл, а не голый бинарь: для голого ad-hoc бинаря TCC не хранит решение «данные других
# приложений» — диалог на каждый запуск. «Полный доступ к диску» выдаётся бандлу вручную.
# Разрешение привязано к подписи, а подпись у пересобранного бандла другая — поэтому бандл
# пересобирается только при изменении исходника, Info.plist или флагов; после пересборки
# доступ выдаётся заново. Прежний голый бинарь bin/whatsapp_snapshot не используется и не удаляется.
#
# --no-load — собрать бандл и положить plist агента, но launchctl не трогать (установка до
# выдачи доступа: без него плановые запуски висят на диалоге TCC).
set -euo pipefail

load_agent=1
for argument in "$@"; do
    case "$argument" in
        --no-load) load_agent=0 ;;
        *) echo "install.sh: неизвестный аргумент $argument (есть только --no-load)" >&2; exit 64 ;;
    esac
done

LABEL="com.sumarokov.personal-assistant.whatsapp-snapshot"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_FILE="$SOURCE_DIR/whatsapp_snapshot.c"
INFO_PLIST="$SOURCE_DIR/Info.plist"
PLIST_TEMPLATE="$SOURCE_DIR/$LABEL.plist"
PA_DATA_DIR="$HOME/docker/personal_assistant"
BIN_DIR="$PA_DATA_DIR/bin"
APP="$BIN_DIR/WhatsAppSnapshot.app"
APP_BUILD="$BIN_DIR/.WhatsAppSnapshot.app.build"
APP_PREVIOUS="$BIN_DIR/.WhatsAppSnapshot.app.previous"
APP_SOURCE_HASH="$APP.source-sha256"
BINARY="$APP/Contents/MacOS/whatsapp_snapshot"
SNAPSHOT_DIR="$PA_DATA_DIR/whatsapp"
LOG_DIR="$HOME/Library/Logs/personal_assistant"
LOG_FILE="$LOG_DIR/whatsapp_snapshot.log"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
BUILD_FLAGS="-O2 -Wall -Wextra -Wpedantic -Werror"
# Ad-hoc подпись всего бандла со стабильным идентификатором (= CFBundleIdentifier).
SIGN_FLAGS="-s - -f --identifier $LABEL"
DOMAIN="gui/$(id -u)"

mkdir -p "$BIN_DIR" "$SNAPSHOT_DIR" "$LOG_DIR" "$(dirname "$PLIST")"

source_hash="$( { cat "$SOURCE_FILE" "$INFO_PLIST"; echo "$BUILD_FLAGS"; echo "$SIGN_FLAGS"; } \
    | shasum -a 256 | awk '{print $1}')"
app_rebuilt=0
if [ ! -x "$BINARY" ] || [ "$(cat "$APP_SOURCE_HASH" 2>/dev/null)" != "$source_hash" ]; then
    rm -rf "$APP_BUILD" "$APP_PREVIOUS"
    mkdir -p "$APP_BUILD/Contents/MacOS"
    plutil -lint "$INFO_PLIST" > /dev/null
    cp "$INFO_PLIST" "$APP_BUILD/Contents/Info.plist"
    # shellcheck disable=SC2086  # флаги сборки — список слов
    cc $BUILD_FLAGS -o "$APP_BUILD/Contents/MacOS/whatsapp_snapshot" "$SOURCE_FILE" -lsqlite3
    # shellcheck disable=SC2086  # флаги подписи — список слов
    codesign $SIGN_FLAGS "$APP_BUILD"
    codesign --verify --deep --strict "$APP_BUILD"
    # Подмена: каталог нельзя переименовать поверх непустого, поэтому два rename подряд.
    if [ -e "$APP" ]; then
        mv "$APP" "$APP_PREVIOUS"
    fi
    mv "$APP_BUILD" "$APP"
    rm -rf "$APP_PREVIOUS"
    echo "$source_hash" > "$APP_SOURCE_HASH"
    app_rebuilt=1
fi

plist_content="$(sed -e "s#@BINARY@#$BINARY#g" -e "s#@LOG_FILE@#$LOG_FILE#g" "$PLIST_TEMPLATE")"
plist_changed=0
if [ ! -f "$PLIST" ] || [ "$(cat "$PLIST")" != "$plist_content" ]; then
    printf '%s\n' "$plist_content" > "$PLIST.tmp"
    plutil -lint "$PLIST.tmp" > /dev/null
    mv -f "$PLIST.tmp" "$PLIST"
    plist_changed=1
fi

if [ "$load_agent" = 1 ]; then
    if launchctl print "$DOMAIN/$LABEL" > /dev/null 2>&1; then
        if [ "$plist_changed" = 1 ]; then
            launchctl bootout "$DOMAIN/$LABEL"
            launchctl bootstrap "$DOMAIN" "$PLIST"
        elif [ "$app_rebuilt" = 1 ]; then
            launchctl kickstart -k "$DOMAIN/$LABEL"
        fi
    else
        launchctl bootstrap "$DOMAIN" "$PLIST"
    fi
else
    echo "whatsapp_snapshot: --no-load — агент не загружен; после выдачи доступа: launchctl bootstrap $DOMAIN $PLIST" >&2
fi

if [ "$app_rebuilt" = 1 ]; then
    echo "whatsapp_snapshot: бандл собран заново — выдать ему «Полный доступ к диску»: $APP" >&2
fi
