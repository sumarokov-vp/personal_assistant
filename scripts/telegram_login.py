# /// script
# requires-python = ">=3.12"
# dependencies = ["telethon>=1.36"]
# ///
# ruff: noqa: S105, S603, S607, T201 — пути к записям pass, не пароли; standalone CLI: печать в терминал, pass через subprocess
"""Войти в Telegram аккаунтом владельца и положить сессию Telethon в pass.

Запуск (из корня репы personal_assistant, на Mac mini — машине с ключом pass ассистента):

    uv run scripts/telegram_login.py

api_id и api_hash приложения my.telegram.org берутся из pass
``assistant/personal_assistant/telegram-app`` (строки ``api_id=`` и ``api_hash=``). Скрипт
спрашивает номер телефона, код из Telegram и пароль двухэтапной проверки, после входа кладёт
строку StringSession в ``assistant/personal_assistant/telegram-user`` через ``pass insert -m``
(stdin, не аргумент процесса).

На экран — только «сохранено», id, имя и @username аккаунта и число диалогов без каналов.
Сессия и api_hash не печатаются. Клиент не принимает апдейты и после входа ставит статус
«не в сети». Если запись сессии уже есть — спросит, перезаписать ли; без «да» старую не трогает.
"""

from __future__ import annotations

import asyncio
import getpass
import io
import os
import subprocess
import sys
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateStatusRequest

APP_PASS_ENTRY = "assistant/personal_assistant/telegram-app"
SESSION_PASS_ENTRY = "assistant/personal_assistant/telegram-user"
DEVICE_MODEL = "Personal Assistant"


def pass_entry_exists(entry: str) -> bool:
    store = Path(os.environ.get("PASSWORD_STORE_DIR", Path.home() / ".password-store"))
    return (store / f"{entry}.gpg").is_file()


def confirm_overwrite() -> bool:
    answer = input(f"В pass уже есть {SESSION_PASS_ENTRY}. Перезаписать? [да/нет]: ")
    return answer.strip().lower() == "да"


def load_app() -> tuple[int, str]:
    raw = subprocess.run(
        ["pass", "show", APP_PASS_ENTRY],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    fields: dict[str, str] = {}
    for line in raw.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            fields[key.strip()] = value.strip()
    api_id = fields.get("api_id", "")
    api_hash = fields.get("api_hash", "")
    if not api_id.isdigit() or not api_hash:
        sys.exit(f"В {APP_PASS_ENTRY} нет строк api_id=<число> и api_hash=<строка>")
    return int(api_id), api_hash


def store_session(session: str) -> None:
    subprocess.run(
        ["pass", "insert", "-m", "-f", SESSION_PASS_ENTRY],
        input=session + "\n",
        check=True,
        text=True,
        stdout=subprocess.DEVNULL,
    )


def ask_phone() -> str:
    return input("Номер телефона (+7...): ").strip()


def ask_code() -> str:
    return input("Код из Telegram (никому не пересылать): ").strip()


def ask_password() -> str:
    return getpass.getpass("Пароль двухэтапной проверки: ")


async def count_dialogs_without_channels(client: TelegramClient) -> int:
    count = 0
    async for dialog in client.iter_dialogs():
        if dialog.is_channel and not dialog.is_group:
            continue
        count += 1
    return count


async def login(api_id: int, api_hash: str) -> None:
    client = TelegramClient(
        StringSession(),
        api_id,
        api_hash,
        receive_updates=False,
        device_model=DEVICE_MODEL,
    )
    await client.start(phone=ask_phone, code_callback=ask_code, password=ask_password)
    try:
        await client(UpdateStatusRequest(offline=True))
        store_session(client.session.save())
        print(f"сохранено в pass {SESSION_PASS_ENTRY}")
        me = await client.get_me()
        name = " ".join(part for part in (me.first_name, me.last_name) if part)
        username = f"@{me.username}" if me.username else "без @username"
        print(f"аккаунт: id {me.id}, {name}, {username}")
        dialogs = await count_dialogs_without_channels(client)
        print(f"диалогов без каналов: {dialogs}")
        await client(UpdateStatusRequest(offline=True))
    finally:
        await client.disconnect()


def main() -> None:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(line_buffering=True)
    if pass_entry_exists(SESSION_PASS_ENTRY) and not confirm_overwrite():
        sys.exit("Оставлена прежняя сессия, ничего не записано")
    api_id, api_hash = load_app()
    asyncio.run(login(api_id, api_hash))


if __name__ == "__main__":
    main()
