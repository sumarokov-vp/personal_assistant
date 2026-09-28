#!/usr/bin/env bash
# Установка launchd-агента хостового сервиса WhatsApp Web (идемпотентно, вызывается из deploy/up.sh).
#
# Chromium под Playwright с постоянным профилем (связанное устройство аккаунта владельца) слушает
# 127.0.0.1:$WHATSAPP_WEB_PORT (умолчание 18790, см. hosts/whatsapp_web/README.md). launchd-агент
# com.sumarokov.personal-assistant.whatsapp-web — RunAtLoad, KeepAlive, GUI-сессия (Chromium её
# требует). Лог — ~/Library/Logs/personal_assistant/whatsapp_web.log.
#
# Рантайм — не в checkout: SOURCE_DIR (hosts/whatsapp_web в той рабочей копии, откуда запущен
# install.sh) копируется rsync'ом в постоянный APP_DIR ~/docker/personal_assistant/whatsapp-web/app
# (переживает удаление/переключение worktree — checkout удалили, gc, сменили ветку — сервис не
# затронут), там же собирается .venv (uv sync --locked --no-dev). ProgramArguments plist — бинарь
# из APP_DIR, а не из checkout. rsync --checksum сравнивает содержимое, не mtime: второй прогон из
# другой копии с тем же кодом ничего не копирует. launchd перезапускается («kickstart -k»), только
# если rsync реально что-то поменял в APP_DIR (новый код/версия) — не на каждый прогон install.sh.
#
# Секреты сервиса — один файл 0600 ~/docker/personal_assistant/secrets/whatsapp-web (каталог 0700):
# первая строка — ключ API, дальше key=value: phone=<номер>, notify_amqp_url=<URL agent-whatsapp-web>
# (нет учётки — строки не будет, сервис пишет сигнал перепривязки в лог и не падает). Ключ и номер —
# pass assistant/personal_assistant/whatsapp-web; нет записи — заводится здесь (ключ — openssl rand,
# номер — вытаскивается из ~/whatsapp-web-spike/scripts/s_num.py, сам скрипт не запускается — WhatsApp
# Web им не трогаем, в репозиторий и в лог номер не попадает).
#
# Две связки GPG на этой машине: $ASSISTANT_GNUPGHOME (up.sh) — только секретная половина ключа
# ассистента, читает assistant/, ничего из work/ не расшифрует; $OPERATOR_GNUPGHOME (fish задаёт
# GNUPGHOME=$XDG_CONFIG_HOME/gnupg всем интерактивным шеллам, ~/.config/gnupg) — обычные ключи
# владельца (в т.ч. публичные половины всех получателей assistant/, нужные, чтобы завести новую
# запись там) и читает work/. Голое `unset GNUPGHOME` — не то же самое: gpg падает на встроенный
# ~/.gnupg, это третье, постороннее хранилище. Учётку agent-whatsapp-web заводит deploy/rabbitmq/
# setup.sh add-source whatsapp-web; её pass-запись (work/local/rabbitmq/assistant-notify/whatsapp-web)
# читается $OPERATOR_GNUPGHOME — независимо от того, что мог экспортировать вызвавший up.sh.
set -euo pipefail

LABEL="com.sumarokov.personal-assistant.whatsapp-web"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SOURCE_DIR/../.." && pwd)"
PLIST_TEMPLATE="$SOURCE_DIR/launchd/$LABEL.plist"

PA_DATA_DIR="$HOME/docker/personal_assistant"
APP_DIR="$PA_DATA_DIR/whatsapp-web/app"
PROGRAM="$APP_DIR/.venv/bin/whatsapp-web-host"
SECRETS_DIR="$PA_DATA_DIR/secrets"
KEY_FILE="$SECRETS_DIR/whatsapp-web"
PROFILE_DIR="$PA_DATA_DIR/whatsapp-web/profile"
SPIKE_DIR="$HOME/whatsapp-web-spike"
SPIKE_PROFILE="$SPIKE_DIR/profile"
SPIKE_NUM_SCRIPT="$SPIKE_DIR/scripts/s_num.py"
LOG_DIR="$HOME/Library/Logs/personal_assistant"
LOG_FILE="$LOG_DIR/whatsapp_web.log"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

PASS_ENTRY="assistant/personal_assistant/whatsapp-web"
ASSISTANT_GNUPGHOME="$HOME/docker/personal_assistant/gnupg"
OPERATOR_GNUPGHOME="$HOME/.config/gnupg"
NOTIFY_ENTRY="work/local/rabbitmq/assistant-notify/whatsapp-web"

say() {
    echo "install.sh (whatsapp-web): $*"
}

( umask 077 && mkdir -p "$SECRETS_DIR" "$PROFILE_DIR" )
chmod 700 "$SECRETS_DIR" "$PROFILE_DIR"
mkdir -p "$LOG_DIR" "$(dirname "$PLIST")" "$APP_DIR"

# --- рантайм: копия проекта в постоянный APP_DIR (не сам checkout — тот может исчезнуть worktree'ом) ---
# --checksum сравнивает содержимое файлов, не mtime: разные рабочие копии с одинаковым кодом дают
# пустой diff. --delete + --exclude '.venv/' не трогает venv в APP_DIR (excluded-файлы rsync по
# умолчанию не удаляет). install.sh, launchd/ и тесты в рантайме не нужны — не копируются.
rsync_diff="$(rsync -a --delete --checksum -i \
    --exclude='.venv/' \
    --exclude='__pycache__/' \
    --exclude='.pytest_cache/' \
    --exclude='.mypy_cache/' \
    --exclude='.ruff_cache/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='tests/' \
    --exclude='conftest.py' \
    --exclude='install.sh' \
    --exclude='launchd/' \
    "$SOURCE_DIR/" "$APP_DIR/")"
runtime_changed=0
if [ -n "$rsync_diff" ] || [ ! -x "$PROGRAM" ]; then
    runtime_changed=1
fi

# --- зависимости: та же сборка Chromium, что у пробного прогона (playwright==1.63.0) ---
# Выполняются всегда (дёшево и идемпотентно при отсутствии изменений), но именно runtime_changed
# (не факт вызова uv sync) решает, перезапускать ли уже работающий launchd-агент ниже.
( cd "$APP_DIR" && uv sync --locked --no-dev --quiet )
( cd "$APP_DIR" && uv run --quiet playwright install chromium )
if [ "$runtime_changed" = 1 ]; then
    say "рантайм обновлён: $APP_DIR"
else
    say "рантайм без изменений: $APP_DIR"
fi

# --- перенос профиля пробного прогона, если своего профиля ещё нет ---
if [ -z "$(ls -A "$PROFILE_DIR" 2>/dev/null)" ] && [ -d "$SPIKE_PROFILE" ]; then
    spike_pids="$(lsof -ti :9222 2>/dev/null || true)"
    if [ -n "$spike_pids" ]; then
        say "спайк-браузер слушает :9222 (pid $spike_pids) — останавливаю перед переносом профиля"
        # shellcheck disable=SC2086  # список pid, не одна строка
        kill $spike_pids 2>/dev/null || true
        for _ in 1 2 3 4 5; do
            lsof -ti :9222 >/dev/null 2>&1 || break
            sleep 1
        done
    fi
    cp -a "$SPIKE_PROFILE/." "$PROFILE_DIR/"
    chmod 700 "$PROFILE_DIR"
    say "профиль перенесён из $SPIKE_PROFILE (исходник не тронут)"
fi

# --- pass: ключ API + номер (связка ассистента — та же, что у up.sh) ---
pass_assistant_first_line() {
    GNUPGHOME="$ASSISTANT_GNUPGHOME" pass show "$1" | head -n 1
}

pass_assistant_field() {
    GNUPGHOME="$ASSISTANT_GNUPGHOME" pass show "$1" | tail -n +2 | sed -n "s/^$2=//p" | awk "NR == 1"
}

if ! GNUPGHOME="$ASSISTANT_GNUPGHOME" pass show "$PASS_ENTRY" > /dev/null 2>&1; then
    say "pass $PASS_ENTRY не найдена — завожу (ключ — openssl rand, номер — из $SPIKE_NUM_SCRIPT)"
    if [ ! -f "$SPIKE_NUM_SCRIPT" ]; then
        say "$SPIKE_NUM_SCRIPT не найден — номер взять неоткуда" >&2
        exit 1
    fi
    api_key="$(openssl rand -hex 32)"
    phone="$(sed -n -E 's/.*\.type\("([0-9]+)".*/\1/p' "$SPIKE_NUM_SCRIPT" | head -n 1)"
    if [ -z "$phone" ]; then
        say "не удалось извлечь номер из $SPIKE_NUM_SCRIPT" >&2
        exit 1
    fi
    # Шифрование новой записи требует публичные ключи всех получателей assistant/ — они есть в
    # $OPERATOR_GNUPGHOME (там и три обычных ключа, и публичная половина ключа ассистента), а не в
    # $ASSISTANT_GNUPGHOME (там только секретная половина ключа ассистента, без чужих публичных)
    printf '%s\nphone=%s\n' "$api_key" "$phone" \
        | GNUPGHOME="$OPERATOR_GNUPGHOME" pass insert --multiline "$PASS_ENTRY" > /dev/null
    unset api_key phone
    say "pass $PASS_ENTRY создана"
fi

api_key="$(pass_assistant_first_line "$PASS_ENTRY")"
phone="$(pass_assistant_field "$PASS_ENTRY" phone)"
if [ -z "$api_key" ] || [ -z "$phone" ]; then
    say "pass $PASS_ENTRY: пустой ключ или номер" >&2
    exit 1
fi

# URL-кодирование поля amqp:// (percent-encode) — из stdin, значение в аргументы процесса не попадает
url_encode() {
    python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read(), safe=""), end="")'
}

# --- учётка RabbitMQ agent-whatsapp-web (уведомление о перепривязке, читает #01a0e7b6-23e6) ---
# Пользователь в amqp-URL обязан совпадать с учёткой (брокер сверяет user_id сообщения);
# host/port — как у skills/telegram/scripts/publish.py (127.0.0.1:5672, умолчание брокера на этой машине).
notify_amqp_url=""
if GNUPGHOME="$OPERATOR_GNUPGHOME" "$REPO_ROOT/deploy/rabbitmq/setup.sh" add-source whatsapp-web; then
    if GNUPGHOME="$OPERATOR_GNUPGHOME" pass show "$NOTIFY_ENTRY" > /dev/null 2>&1; then
        notify_password="$(GNUPGHOME="$OPERATOR_GNUPGHOME" pass show "$NOTIFY_ENTRY" | head -n 1)"
        notify_user="$(GNUPGHOME="$OPERATOR_GNUPGHOME" pass show "$NOTIFY_ENTRY" | tail -n +2 | sed -n 's/^user=//p')"
        notify_vhost="$(GNUPGHOME="$OPERATOR_GNUPGHOME" pass show "$NOTIFY_ENTRY" | tail -n +2 | sed -n 's/^vhost=//p')"
        if [ -n "$notify_password" ] && [ -n "$notify_user" ] && [ -n "$notify_vhost" ]; then
            # rabbitmq на этой машине публикует 5672 только на 127.0.0.1 (~/docker/rabbitmq/docker-compose.yml)
            notify_amqp_url="amqp://$(printf '%s' "$notify_user" | url_encode):$(printf '%s' "$notify_password" | url_encode)@127.0.0.1:5672/${notify_vhost}"
        fi
        unset notify_password
    fi
else
    say "deploy/rabbitmq/setup.sh add-source whatsapp-web не выполнился — notify_amqp_url не пишется, сервис сигналит только в лог" >&2
fi

# --- файл секретов: перезаписывается только при изменении содержимого ---
(
    umask 077
    {
        printf '%s\n' "$api_key"
        printf 'phone=%s\n' "$phone"
        if [ -n "$notify_amqp_url" ]; then
            printf 'notify_amqp_url=%s\n' "$notify_amqp_url"
        fi
    } > "$KEY_FILE.tmp"
)
unset api_key phone notify_amqp_url
if [ -f "$KEY_FILE" ] && cmp -s "$KEY_FILE.tmp" "$KEY_FILE"; then
    rm -f "$KEY_FILE.tmp"
else
    mv -f "$KEY_FILE.tmp" "$KEY_FILE"
    say "файл секретов обновлён: $KEY_FILE"
fi
chmod 600 "$KEY_FILE"

# --- launchd ---
plist_content="$(sed \
    -e "s#@PROGRAM@#$PROGRAM#g" \
    -e "s#@KEY_FILE@#$KEY_FILE#g" \
    -e "s#@LOG_FILE@#$LOG_FILE#g" \
    "$PLIST_TEMPLATE")"
plist_changed=0
if [ ! -f "$PLIST" ] || [ "$(cat "$PLIST")" != "$plist_content" ]; then
    printf '%s\n' "$plist_content" > "$PLIST.tmp"
    plutil -lint "$PLIST.tmp" > /dev/null
    mv -f "$PLIST.tmp" "$PLIST"
    plist_changed=1
fi

# launchd сразу после bootout иногда отвечает на bootstrap транзиентным "Input/output error" (5) —
# домен ещё не освободил label. Несколько попыток с паузой вместо падения install.sh.
bootstrap_with_retry() {
    local attempt
    for attempt in 1 2 3 4 5; do
        if launchctl bootstrap "$DOMAIN" "$PLIST" 2>/dev/null; then
            return 0
        fi
        sleep 1
    done
    launchctl bootstrap "$DOMAIN" "$PLIST"
}

if launchctl print "$DOMAIN/$LABEL" > /dev/null 2>&1; then
    if [ "$plist_changed" = 1 ]; then
        launchctl bootout "$DOMAIN/$LABEL"
        bootstrap_with_retry
        say "агент перезагружен (plist изменился)"
    elif [ "$runtime_changed" = 1 ]; then
        launchctl kickstart -k "$DOMAIN/$LABEL"
        say "агент перезапущен (рантайм изменился)"
    else
        say "агент без изменений"
    fi
else
    bootstrap_with_retry
    say "агент загружен"
fi
