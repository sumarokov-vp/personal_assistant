#!/usr/bin/env bash
# Почта ассистентов компании: vhost assistants.<компания> в общем брокере rabbitmq на Mac mini
# (~/docker/rabbitmq, сеть infra). Идемпотентен: повторный запуск ничего не меняет.
#
#   deploy/rabbitmq/assistants.sh                      vhost, exchange, сверка ящиков и учёток
#                                                      ассистентов, чьи записи уже есть в pass
#   deploy/rabbitmq/assistants.sh add-assistant <ключ> ящик и учётка ассистента <ключ>
#
# Топология: exchange assistant-mail (direct, durable); ключ маршрута — ключ адресата;
# ящик ассистента — очередь inbox.<ключ> (classic, durable), binding по его ключу. Права:
#   assistant-<ключ>   configure ^$  write ^assistant-mail$  read ^inbox\.<ключ>$
# Писать можно любому коллеге, читать — только свой ящик. Отправитель — свойство user_id,
# брокер сверяет его с учёткой, подделать нельзя.
#
# Пароли живут только в pass и уходят в rabbitmqctl через stdin — не в аргументы процессов,
# не в файлы, не в вывод:
#   assistant/personal_assistant/assistant-mail    ассистент владельца (ключ sumarokov):
#                                                  первая строка — ASSISTANT_MAIL_URL бота
#                                                  (amqp://assistant-sumarokov:…@rabbitmq:5672/assistants.sumarokov)
#   work/local/rabbitmq/assistant-mail/<ключ>      прочие (тестовый собеседник и т.п.): первая
#                                                  строка — пароль, ниже user=, vhost=, exchange=, queue=
# Записи шифруются на получателей из .gpg-id своих веток, поэтому пишутся обычным GNUPGHOME.
# Запись владельца бот читает связкой ассистента — скрипт это проверяет.
#
# Vhost assistant (уведомления агентов, setup.sh) и vhost / скрипт не трогает.
set -euo pipefail

CONTAINER="${RABBITMQ_CONTAINER:-rabbitmq}"
COMPANY="sumarokov"
VHOST="assistants.$COMPANY"
EXCHANGE="assistant-mail"
OWNER_KEY="sumarokov"
OWNER_ENTRY="assistant/personal_assistant/assistant-mail"
OTHER_ROOT="work/local/rabbitmq/assistant-mail"
ASSISTANT_GNUPGHOME="$HOME/docker/personal_assistant/gnupg"
STORE="${PASSWORD_STORE_DIR:-$HOME/.password-store}"

# timeout внутри контейнера — страховка от зависшего rabbitmqctl
rmq() {
    docker exec -i "$CONTAINER" timeout 60 rabbitmqctl --quiet "$@"
}

# Команды с паролем на stdin: с --quiet rabbitmqctl 4.3 stdin не читает и висит, поэтому без
# него, а вывод (строка «Password:», без самого пароля) глушится вызывающим
rmq_stdin() {
    docker exec -i "$CONTAINER" timeout 60 rabbitmqctl "$@"
}

say() {
    echo "assistants.sh: $*"
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

# import_definitions со stdin в rabbitmqctl 4.3 висит — JSON кладётся во временный файл внутри
# контейнера (секретов в нём нет) и удаляется. Импорт декларативный: существующее не меняется
import_definitions() {
    docker exec -i "$CONTAINER" sh -c '
        f="$(mktemp)" && cat >"$f" &&
        timeout 60 rabbitmqctl --quiet import_definitions --format json "$f"; rc=$?; rm -f "$f"; exit $rc
    ' >/dev/null
}

setup_topology() {
    import_definitions <<EOF
{
  "vhosts": [{"name": "$VHOST"}],
  "exchanges": [
    {"name": "$EXCHANGE", "vhost": "$VHOST", "type": "direct", "durable": true,
     "auto_delete": false, "internal": false, "arguments": {}}
  ]
}
EOF
    say "топология $VHOST: exchange $EXCHANGE (direct)"
}

setup_inbox() {
    local key="$1" queue="inbox.$1"
    import_definitions <<EOF
{
  "queues": [
    {"name": "$queue", "vhost": "$VHOST", "durable": true, "auto_delete": false,
     "arguments": {"x-queue-type": "classic"}}
  ],
  "bindings": [
    {"source": "$EXCHANGE", "vhost": "$VHOST", "destination": "$queue",
     "destination_type": "queue", "routing_key": "$key", "arguments": {}}
  ]
}
EOF
    say "ящик $queue: $EXCHANGE --$key--> $queue"
}

entry_for() {
    if [ "$1" = "$OWNER_KEY" ]; then
        echo "$OWNER_ENTRY"
    else
        echo "$OTHER_ROOT/$1"
    fi
}

# Пароль учётки из записи pass: у владельца первая строка — URL, у прочих — сам пароль
assistant_password() {
    if [ "$ASSISTANT_ENTRY" = "$OWNER_ENTRY" ]; then
        pass show "$ASSISTANT_ENTRY" | head -n 1 | sed -E 's#^amqp://[^:]+:([^@]+)@.*$#\1#'
    else
        pass show "$ASSISTANT_ENTRY" | head -n 1
    fi
}

setup_assistant() {
    local key="$1"
    if ! [[ "$key" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
        say "ключ ассистента — латиница в нижнем регистре, цифры и дефис: $key" >&2
        exit 1
    fi
    local user="assistant-$key" entry
    entry="$(entry_for "$key")"
    if ! pass_has "$entry"; then
        local password
        password="$(new_password)"
        if [ "$entry" = "$OWNER_ENTRY" ]; then
            printf 'amqp://%s:%s@rabbitmq:5672/%s\n' "$user" "$password" "$VHOST" \
                | pass insert --multiline "$entry" >/dev/null
        else
            printf '%s\nuser=%s\nvhost=%s\nexchange=%s\nqueue=inbox.%s\n' \
                "$password" "$user" "$VHOST" "$EXCHANGE" "$key" \
                | pass insert --multiline "$entry" >/dev/null
        fi
        unset password
        say "pass $entry создана"
    fi
    if [ "$entry" = "$OWNER_ENTRY" ] \
        && ! GNUPGHOME="$ASSISTANT_GNUPGHOME" pass show "$entry" >/dev/null 2>&1; then
        say "pass $entry не расшифровывается связкой ассистента ($ASSISTANT_GNUPGHOME)" >&2
        exit 1
    fi
    setup_inbox "$key"
    ASSISTANT_ENTRY="$entry"
    sync_user "$user" assistant_password
    sync_permissions "$user" '^$' "^${EXCHANGE}\$" "^inbox\\.${key}\$"
}

# Ассистенты, чьи записи уже есть в pass: после потери данных брокера всё встаёт заново
sync_known_assistants() {
    local file
    if pass_has "$OWNER_ENTRY"; then
        setup_assistant "$OWNER_KEY"
    fi
    [ -d "$STORE/$OTHER_ROOT" ] || return 0
    for file in "$STORE/$OTHER_ROOT"/*.gpg; do
        [ -e "$file" ] || continue
        setup_assistant "$(basename "$file" .gpg)"
    done
}

main() {
    check_broker
    case "${1:-}" in
        "")
            setup_topology
            sync_known_assistants
            ;;
        add-assistant)
            if [ $# -ne 2 ]; then
                say "использование: assistants.sh add-assistant <ключ>" >&2
                exit 2
            fi
            setup_topology
            setup_assistant "$2"
            ;;
        *)
            say "использование: assistants.sh [add-assistant <ключ>]" >&2
            exit 2
            ;;
    esac
}

main "$@"
