# /// script
# requires-python = ">=3.12"
# dependencies = ["pika>=1.3"]
# ///
# ruff: noqa: S105, S603, S607, T201 — путь к записи pass, не пароль; standalone CLI: печать в терминал, pass через subprocess
"""Тестовый собеседник почты ассистентов: пишет и читает учёткой коллеги, а не ассистента.

Запуск на Mac mini (брокер на 127.0.0.1:5672), из корня репы personal_assistant:

    uv run scripts/colleague_peer.py send --to sumarokov --type remark --about-agent lawyer --text "…"
    uv run scripts/colleague_peer.py send --to sumarokov --type remark --text "…" --forge-from sumarokov
    uv run scripts/colleague_peer.py get

Учётка — запись pass ``work/local/rabbitmq/assistant-mail/<ключ>`` (по умолчанию ``test``):
первая строка — пароль, ниже ``user=``, ``vhost=``, ``exchange=``, ``queue=``. Её заводит
``deploy/rabbitmq/assistants.sh add-assistant <ключ>``.

``send`` — формат v1 (как ``MailBody``): свойства ``message_id``, ``user_id`` (учётка), ``timestamp``,
``type``; тело JSON ``{v, from, to, type, text, in_reply_to?, about_agent?}``. Publisher confirm +
mandatory: печатается ``in_recipient_inbox``, ``no_recipient`` или ``broker_unavailable``.
``--forge-from`` подменяет ``from`` в теле (user_id остаётся настоящим) — проверка, что получатель
такое письмо отвергает.

``get`` — забрать всё из своего ящика (basic_get, ack), напечатать свойства и тело.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass

import pika
import pika.exceptions

PASS_PREFIX = "work/local/rabbitmq/assistant-mail"
ACCOUNT_PREFIX = "assistant-"
HOST = "127.0.0.1"
PORT = 5672
MESSAGE_TYPES = ("remark", "question", "answer")


@dataclass(frozen=True)
class PeerAccount:
    user: str
    password: str
    vhost: str
    exchange: str
    queue: str

    @property
    def key(self) -> str:
        return self.user.removeprefix(ACCOUNT_PREFIX)


def read_account(key: str) -> PeerAccount:
    entry = subprocess.run(
        ["pass", "show", f"{PASS_PREFIX}/{key}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    fields = dict(line.split("=", 1) for line in entry[1:] if "=" in line)
    return PeerAccount(
        user=fields["user"],
        password=entry[0],
        vhost=fields["vhost"],
        exchange=fields["exchange"],
        queue=fields["queue"],
    )


def connect(account: PeerAccount) -> pika.BlockingConnection:
    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host=HOST,
            port=PORT,
            virtual_host=account.vhost,
            credentials=pika.PlainCredentials(account.user, account.password),
        ),
    )


def send(account: PeerAccount, args: argparse.Namespace) -> int:
    body: dict[str, object] = {
        "v": 1,
        "from": args.forge_from or account.key,
        "to": args.to,
        "type": args.type,
        "text": args.text,
    }
    if args.in_reply_to:
        body["in_reply_to"] = args.in_reply_to
    if args.about_agent:
        body["about_agent"] = args.about_agent
    message_id = str(uuid.uuid4())
    properties = pika.BasicProperties(
        message_id=message_id,
        user_id=account.user,
        timestamp=int(time.time()),
        type=args.type,
        content_type="application/json",
        delivery_mode=pika.DeliveryMode.Persistent,
    )
    try:
        connection = connect(account)
    except pika.exceptions.AMQPError as error:
        print(f"broker_unavailable: {error!r}")
        return 1
    try:
        channel = connection.channel()
        channel.confirm_delivery()
        channel.basic_publish(
            exchange=account.exchange,
            routing_key=args.to,
            body=json.dumps(body, ensure_ascii=False).encode(),
            properties=properties,
            mandatory=True,
        )
    except pika.exceptions.UnroutableError:
        print(f"no_recipient message_id={message_id}")
        return 1
    except pika.exceptions.AMQPError as error:
        print(f"broker_unavailable: {error!r}")
        return 1
    finally:
        if connection.is_open:
            connection.close()
    print(
        f"in_recipient_inbox message_id={message_id} from={body['from']} to={args.to}"
    )
    return 0


def get(account: PeerAccount) -> int:
    connection = connect(account)
    try:
        channel = connection.channel()
        count = 0
        while True:
            method, properties, body = channel.basic_get(account.queue)
            if method is None:
                break
            count += 1
            print(
                f"--- message_id={properties.message_id} user_id={properties.user_id} "
                f"type={properties.type} timestamp={properties.timestamp}",
            )
            print(body.decode())
            channel.basic_ack(method.delivery_tag)
    finally:
        connection.close()
    print(f"{account.queue}: {count} message(s)")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--as", dest="key", default="test", help="ключ собеседника в pass"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    send_parser = commands.add_parser("send", help="написать ассистенту")
    send_parser.add_argument("--to", required=True, help="ключ адресата")
    send_parser.add_argument("--type", choices=MESSAGE_TYPES, default="remark")
    send_parser.add_argument("--text", required=True)
    send_parser.add_argument("--in-reply-to")
    send_parser.add_argument("--about-agent")
    send_parser.add_argument("--forge-from", help="подменить from в теле")
    commands.add_parser("get", help="забрать свой ящик")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    account = read_account(args.key)
    if args.command == "send":
        return send(account, args)
    return get(account)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
