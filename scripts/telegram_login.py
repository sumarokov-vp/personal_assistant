# /// script
# requires-python = ">=3.12"
# dependencies = ["telethon>=1.36"]
# ///
# ruff: noqa: S105, S603, S607, T201 — пути к записям pass, не пароли; standalone CLI: печать в терминал, pass через subprocess
"""Войти в Telegram аккаунтом владельца и положить сессию Telethon в pass.

Запуск (из корня репы personal_assistant, на Mac mini — машине с ключом pass ассистента):

    uv run scripts/telegram_login.py --check   # только подключение: DC, адрес, тестовая ли среда
    uv run scripts/telegram_login.py           # вход

api_id и api_hash приложения my.telegram.org берутся из pass
``assistant/personal_assistant/telegram-app`` (строки ``api_id=`` и ``api_hash=``).

Вход идёт явными шагами, а не ``client.start``: подключение и печать, куда подключились;
номер — нормализуется и подтверждается до отправки кода; после отправки печатается, каким
способом Telegram отправил код, каким отправит повторно и через сколько секунд это можно.
В одном процессе: код — вход; пустой ввод или ``r`` — повторная отправка следующим способом;
``q`` — отмена кода и выход. Неверный код и неверный пароль 2FA спрашиваются снова без новой
отправки. FLOOD_WAIT и прочие отказы Telegram не повторяются: печатается причина и выход.

После входа строка StringSession кладётся в ``assistant/personal_assistant/telegram-user``
через ``pass insert -m`` (stdin, не аргумент процесса). На экран — только «сохранено», id,
имя и @username аккаунта и число диалогов без каналов; сессия, api_hash и код не печатаются.
Клиент не принимает апдейты и после входа ставит статус «не в сети». Если запись сессии уже
есть — спросит, перезаписать ли; без «да» старую не трогает.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import io
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from telethon.tl import types
from telethon.tl.functions.account import UpdateStatusRequest
from telethon.tl.functions.auth import (
    CancelCodeRequest,
    ResendCodeRequest,
    SendCodeRequest,
)
from telethon.tl.functions.help import GetConfigRequest

APP_PASS_ENTRY = "assistant/personal_assistant/telegram-app"
SESSION_PASS_ENTRY = "assistant/personal_assistant/telegram-user"
DEVICE_MODEL = "Personal Assistant"
PHONE_PATTERN = re.compile(r"\+\d{7,15}")
PHONE_SEPARATORS = re.compile(r"[\s()\-.]")


class LoginCancelledError(Exception):
    pass


@dataclass
class CodeRequest:
    phone: str
    phone_code_hash: str
    next_type: object | None
    resend_available_at: float
    expired: bool = False


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


def normalize_phone(raw: str) -> str | None:
    phone = PHONE_SEPARATORS.sub("", raw)
    return phone if PHONE_PATTERN.fullmatch(phone) else None


def ask_phone() -> str:
    while True:
        phone = normalize_phone(
            input("Номер телефона в международном формате (+7...): ")
        )
        if phone is None:
            print(
                "Номер должен начинаться с + и кода страны, дальше только цифры (7–15)"
            )
            continue
        answer = input(f"Отправить код на {phone}? [да/нет]: ")
        if answer.strip().lower() == "да":
            return phone


def ask_password() -> str:
    while True:
        password = getpass.getpass("Пароль двухэтапной проверки: ")
        if password:
            return password


def type_name(code_type: object, prefix: str) -> str:
    return type(code_type).__name__.removeprefix(prefix)


def describe_sent_type(sent_type: object) -> str:
    match sent_type:
        case types.auth.SentCodeTypeApp():
            return "код в чате «Telegram» на другом вашем устройстве, где аккаунт уже открыт"
        case types.auth.SentCodeTypeSms():
            return "SMS на номер"
        case types.auth.SentCodeTypeSmsWord() | types.auth.SentCodeTypeSmsPhrase():
            return "SMS со словом или фразой — ввести их вместо цифр"
        case types.auth.SentCodeTypeCall():
            return "голосовой звонок, код продиктуют"
        case types.auth.SentCodeTypeFlashCall():
            return "сброшенный звонок: код — номер звонившего"
        case types.auth.SentCodeTypeMissedCall(prefix=prefix, length=length):
            return f"пропущенный звонок с номера {prefix}…: код — последние {length} цифр номера"
        case types.auth.SentCodeTypeEmailCode(email_pattern=email_pattern):
            return f"код на почту {email_pattern}"
        case types.auth.SentCodeTypeFragmentSms(url=url):
            return f"код на анонимный номер Fragment: {url}"
        case types.auth.SentCodeTypeFirebaseSms():
            return (
                "SMS через Firebase — стороннему приложению обычно не доходит, лучше r"
            )
        case types.auth.SentCodeTypeSetUpEmailRequired():
            return "Telegram требует сначала привязать почту — скрипт этого не умеет, вход с телефона"
        case _:
            return "способ, неизвестный скрипту"


def describe_sent_code(sent: types.auth.SentCode) -> None:
    kind = type_name(sent.type, "SentCodeType")
    print(f"Код отправлен: {kind} — {describe_sent_type(sent.type)}")
    if sent.next_type is not None:
        print(
            f"Повторная отправка (r) пойдёт способом: {type_name(sent.next_type, 'CodeType')}"
        )
    else:
        print("Другого способа отправки Telegram не предлагает")
    if sent.timeout:
        print(f"Повторить отправку можно через {sent.timeout} с")


def remember_sent_code(phone: str, sent: object) -> CodeRequest:
    match sent:
        case types.auth.SentCode():
            describe_sent_code(sent)
            return CodeRequest(
                phone=phone,
                phone_code_hash=sent.phone_code_hash,
                next_type=sent.next_type,
                resend_available_at=time.monotonic() + (sent.timeout or 0),
            )
        case types.auth.SentCodePaymentRequired():
            sys.exit(
                "Telegram требует платную проверку номера — вход скриптом невозможен"
            )
        case _:
            sys.exit(
                f"Неожиданный ответ Telegram на отправку кода: {type(sent).__name__}"
            )


def humanize_seconds(seconds: int) -> str:
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    parts = [
        f"{hours} ч" if hours else "",
        f"{minutes} мин" if minutes else "",
        f"{secs} с" if secs else "",
    ]
    return " ".join(part for part in parts if part) or "0 с"


async def print_connection(client: TelegramClient) -> None:
    config = await client(GetConfigRequest())
    session = client.session
    print(
        f"Подключение: DC {session.dc_id}, адрес {session.server_address}:{session.port}"
    )
    environment = (
        "да — ТЕСТОВЫЕ серверы" if config.test_mode else "нет, боевые серверы Telegram"
    )
    print(f"Telegram: this_dc {config.this_dc}, тестовая среда: {environment}")


async def send_code(
    client: TelegramClient, api_id: int, api_hash: str, phone: str
) -> CodeRequest:
    sent = await client(SendCodeRequest(phone, api_id, api_hash, types.CodeSettings()))
    print(f"Номер обслуживает DC {client.session.dc_id}")
    return remember_sent_code(phone, sent)


async def resend_code(
    client: TelegramClient, api_id: int, api_hash: str, request: CodeRequest
) -> CodeRequest:
    if request.expired:
        print("Прежний код истёк — запрашиваю новый")
        return await send_code(client, api_id, api_hash, request.phone)
    if request.next_type is None:
        print("Другого способа нет: ждите код или q — выход")
        return request
    wait = request.resend_available_at - time.monotonic()
    if wait > 0:
        print(f"Повторить отправку можно через {int(wait) + 1} с — пока ждите код")
        return request
    sent = await client(ResendCodeRequest(request.phone, request.phone_code_hash))
    return remember_sent_code(request.phone, sent)


async def sign_in_with_password(client: TelegramClient) -> None:
    while True:
        try:
            await client.sign_in(password=ask_password())
            return
        except errors.PasswordHashInvalidError:
            print("Пароль неверный, ещё раз")


async def sign_in(client: TelegramClient, api_id: int, api_hash: str) -> None:
    request = await send_code(client, api_id, api_hash, ask_phone())
    while True:
        entry = input(
            "Код (Enter или r — отправить другим способом, q — выход): "
        ).strip()
        if entry.lower() == "q":
            await client(CancelCodeRequest(request.phone, request.phone_code_hash))
            raise LoginCancelledError
        if entry.lower() in ("", "r"):
            request = await resend_code(client, api_id, api_hash, request)
            continue
        try:
            await client.sign_in(
                request.phone, entry, phone_code_hash=request.phone_code_hash
            )
            return
        except errors.PhoneCodeInvalidError:
            print("Код неверный, введите ещё раз (новый код не отправлялся)")
        except errors.PhoneCodeExpiredError:
            request.expired = True
            print("Код истёк — r запросит новый")
        except errors.SessionPasswordNeededError:
            await sign_in_with_password(client)
            return


async def count_dialogs_without_channels(client: TelegramClient) -> int:
    count = 0
    async for dialog in client.iter_dialogs():
        if dialog.is_channel and not dialog.is_group:
            continue
        count += 1
    return count


async def save_and_report(client: TelegramClient) -> None:
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


def build_client(api_id: int, api_hash: str) -> TelegramClient:
    return TelegramClient(
        StringSession(),
        api_id,
        api_hash,
        receive_updates=False,
        device_model=DEVICE_MODEL,
        flood_sleep_threshold=0,
    )


async def check(api_id: int, api_hash: str) -> None:
    client = build_client(api_id, api_hash)
    await client.connect()
    try:
        await print_connection(client)
    finally:
        await client.disconnect()


async def login(api_id: int, api_hash: str) -> None:
    client = build_client(api_id, api_hash)
    await client.connect()
    try:
        await print_connection(client)
        await sign_in(client, api_id, api_hash)
        await save_and_report(client)
    finally:
        await client.disconnect()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Вход владельца в Telegram, сессия — в pass"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="только подключиться и показать DC, адрес и тестовая ли среда; без номера и кода",
    )
    return parser.parse_args()


def run(args: argparse.Namespace) -> None:
    if args.check:
        api_id, api_hash = load_app()
        asyncio.run(check(api_id, api_hash))
        return
    if pass_entry_exists(SESSION_PASS_ENTRY) and not confirm_overwrite():
        sys.exit("Оставлена прежняя сессия, ничего не записано")
    api_id, api_hash = load_app()
    asyncio.run(login(api_id, api_hash))


def main() -> None:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(line_buffering=True)
    args = parse_args()
    try:
        run(args)
    except LoginCancelledError:
        sys.exit("Отправка кода отменена, ничего не записано")
    except (errors.FloodWaitError, errors.FloodPremiumWaitError) as error:
        sys.exit(
            f"Telegram ограничил попытки: ждать {humanize_seconds(error.seconds)}. "
            "Не перезапускать раньше — каждый запуск продлевает ожидание"
        )
    except errors.SendCodeUnavailableError:
        sys.exit(
            "Telegram исчерпал способы отправки кода для этого номера — повторить позже"
        )
    except errors.RPCError as error:
        sys.exit(
            f"Telegram отказал: {error.message} (код {error.code}), ничего не записано"
        )
    except (KeyboardInterrupt, EOFError):
        sys.exit("\nПрервано, ничего не записано")


if __name__ == "__main__":
    main()
