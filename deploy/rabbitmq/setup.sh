#!/usr/bin/env bash
# Уведомления рабочих агентов: vhost assistant в общем брокере rabbitmq на Mac mini
# (~/docker/rabbitmq, сеть infra). Идемпотентен: повторный запуск ничего не меняет.
#
#   deploy/rabbitmq/setup.sh                   vhost, топология, учётка pa-consumer,
#                                              сверка учёток уже заведённых источников
#   deploy/rabbitmq/setup.sh add-source <имя>  учётка отправителя agent-<имя>
#
# Топология — definitions.json рядом (без учёток и паролей): exchange agent-notify (fanout)
# → очередь pa.notifications. Права:
#   pa-consumer    configure ^$  write ^$              read ^pa\.notifications$
#   agent-<имя>    configure ^$  write ^agent-notify$  read ^$
#
# Пароли живут только в pass и уходят в rabbitmqctl через stdin — не в аргументы процессов,
# не в файлы, не в вывод:
#   assistant/personal_assistant/rabbitmq          первая строка — RABBITMQ_URL бота
#                                                  (amqp://pa-consumer:…@rabbitmq:5672/assistant)
#   work/local/rabbitmq/assistant-notify/<имя>     первая строка — пароль agent-<имя>,
#                                                  ниже user=, vhost=, exchange=
# Записи шифруются на получателей из .gpg-id своих веток (ключи этой машины и ключ ассистента
# для assistant/), поэтому пишутся обычным GNUPGHOME: в связке ассистента чужих публичных
# ключей нет. Бот читает свою запись связкой ассистента — setup.sh это проверяет.
#
# Vhost / и его учётки (supplements) скрипт не трогает.
set -euo pipefail

CONTAINER="${RABBITMQ_CONTAINER:-rabbitmq}"
VHOST="assistant"
EXCHANGE="agent-notify"
QUEUE="pa.notifications"
CONSUMER_USER="pa-consumer"
CONSUMER_ENTRY="assistant/personal_assistant/rabbitmq"
SOURCE_ROOT="work/local/rabbitmq/assistant-notify"
ASSISTANT_GNUPGHOME="$HOME/docker/personal_assistant/gnupg"
STORE="${PASSWORD_STORE_DIR:-$HOME/.password-store}"

DEFINITIONS="$(cd "$(dirname "$0")" && pwd)/definitions.json"

# timeout внутри контейнера — страховка от зависшего rabbitmqctl
rmq() {
    docker exec -i "$CONTAINER" timeout 60 rabbitmqctl --quiet "$@"
}

# Команды с паролем на stdin: с --quiet rabbitmqctl 4.3 stdin не читает и
# висит, поэтому без него, а вывод (строка «Password:», без самого пароля) глушится вызывающим
rmq_stdin() {
    docker exec -i "$CONTAINER" timeout 60 rabbitmqctl "$@"
}

say() {
    echo "setup.sh: $*"
}

pass_has() {
    [ -f "$STORE/$1.gpg" ]
}

new_password() {
    # hex — без символов, которые пришлось бы экранировать в AMQP URL
    openssl rand -hex 24
}

user_exists() {
    rmq list_users --silent --no-table-headers | awk '{print $1}' | grep -qx -- "$1"
}

# Учётка брокера по паролю из pass: нет — заводится, есть, но пароль разошёлся с pass —
# пароль приводится к pass. Пароль приходит на stdin от $2 (функции, читающей pass).
sync_user() {
    local user="$1" password_fn="$2"
    if ! user_exists "$user"; then
        "$password_fn" | rmq_stdin add_user "$user" >/dev/null
        say "учётка $user заведена"
    elif ! "$password_fn" | rmq_stdin authenticate_user "$user" >/dev/null 2>&1; then
        "$password_fn" | rmq_stdin change_password "$user" >/dev/null
        say "учётка $user: пароль приведён к pass"
    else
        say "учётка $user без изменений"
    fi
}

# set_permissions только при расхождении — повторный запуск не шлёт брокеру ничего
sync_permissions() {
    local user="$1" configure="$2" write="$3" read="$4" want current
    want="$(printf '%s\t%s\t%s\t%s' "$user" "$configure" "$write" "$read")"
    current="$(rmq list_permissions -p "$VHOST" --silent --no-table-headers | awk -F '\t' -v u="$user" '$1 == u')"
    if [ "$current" = "$want" ]; then
        say "права $user в $VHOST без изменений"
    else
        rmq set_permissions -p "$VHOST" "$user" "$configure" "$write" "$read" >/dev/null
        say "права $user в $VHOST выставлены: configure $configure, write $write, read $read"
    fi
}

check_broker() {
    if ! rmq status >/dev/null 2>&1; then
        say "брокер $CONTAINER не отвечает (docker exec $CONTAINER rabbitmqctl status)" >&2
        exit 1
    fi
}

setup_topology() {
    # import_definitions со stdin в rabbitmqctl 4.3 висит — файл кладётся во временный внутри
    # контейнера (секретов в нём нет) и удаляется
    docker exec -i "$CONTAINER" sh -c '
        f="$(mktemp)" && cat >"$f" &&
        timeout 60 rabbitmqctl --quiet import_definitions --format json "$f"; rc=$?; rm -f "$f"; exit $rc
    ' <"$DEFINITIONS" >/dev/null
    say "топология $VHOST: exchange $EXCHANGE (fanout) → очередь $QUEUE"
}

consumer_password() {
    pass show "$CONSUMER_ENTRY" | head -n 1 | sed -E 's#^amqp://[^:]+:([^@]+)@.*$#\1#'
}

setup_consumer() {
    if ! pass_has "$CONSUMER_ENTRY"; then
        local password
        password="$(new_password)"
        printf 'amqp://%s:%s@rabbitmq:5672/%s\n' "$CONSUMER_USER" "$password" "$VHOST" \
            | pass insert --multiline "$CONSUMER_ENTRY" >/dev/null
        unset password
        say "pass $CONSUMER_ENTRY создана"
    fi
    if ! GNUPGHOME="$ASSISTANT_GNUPGHOME" pass show "$CONSUMER_ENTRY" >/dev/null 2>&1; then
        say "pass $CONSUMER_ENTRY не расшифровывается связкой ассистента ($ASSISTANT_GNUPGHOME)" >&2
        exit 1
    fi
    sync_user "$CONSUMER_USER" consumer_password
    sync_permissions "$CONSUMER_USER" '^$' '^$' "^${QUEUE//./\\.}\$"
}

setup_source() {
    local name="$1"
    if ! [[ "$name" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
        say "имя источника — латиница в нижнем регистре, цифры и дефис: $name" >&2
        exit 1
    fi
    local user="agent-$name" entry="$SOURCE_ROOT/$name"
    if ! pass_has "$entry"; then
        local password
        password="$(new_password)"
        printf '%s\nuser=%s\nvhost=%s\nexchange=%s\n' "$password" "$user" "$VHOST" "$EXCHANGE" \
            | pass insert --multiline "$entry" >/dev/null
        unset password
        say "pass $entry создана"
    fi
    SOURCE_ENTRY="$entry"
    sync_user "$user" source_password
    sync_permissions "$user" '^$' "^${EXCHANGE}\$" '^$'
}

source_password() {
    pass show "$SOURCE_ENTRY" | head -n 1
}

# Источники, чьи записи уже есть в pass: после потери данных брокера учётки встают заново
sync_known_sources() {
    local file name
    [ -d "$STORE/$SOURCE_ROOT" ] || return 0
    for file in "$STORE/$SOURCE_ROOT"/*.gpg; do
        [ -e "$file" ] || continue
        name="$(basename "$file" .gpg)"
        setup_source "$name"
    done
}

main() {
    check_broker
    case "${1:-}" in
        "")
            setup_topology
            setup_consumer
            sync_known_sources
            ;;
        add-source)
            if [ $# -ne 2 ]; then
                say "использование: setup.sh add-source <имя>" >&2
                exit 2
            fi
            setup_topology
            setup_source "$2"
            ;;
        *)
            say "использование: setup.sh [add-source <имя>]" >&2
            exit 2
            ;;
    esac
}

main "$@"
