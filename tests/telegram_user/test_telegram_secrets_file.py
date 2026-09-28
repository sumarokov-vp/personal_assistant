import asyncio
from pathlib import Path

import pytest

from src.telegram_user.errors.telegram_secrets_file_error import (
    TelegramSecretsFileError,
)
from src.telegram_user.errors.telegram_timeout_error import TelegramTimeoutError
from src.telegram_user.models.telegram_credentials import TelegramCredentials
from src.telegram_user.repos.event_loop_thread import EventLoopThread
from src.telegram_user.repos.telegram_secrets_file import TelegramSecretsFile
from src.telegram_user.repos.telethon_client_factory import TelethonClientFactory

SESSION = "1BVtsOK8Bu0aZ-synthetic-session=="
API_HASH = "0123456789abcdef0123456789abcdef"


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "telegram_user"
    path.write_text(text, encoding="utf-8")
    return path


def test_reads_session_api_id_api_hash_lines(tmp_path: Path) -> None:
    path = write(tmp_path, f"session={SESSION}\napi_id=123456\napi_hash={API_HASH}\n")

    credentials = TelegramSecretsFile(path).read()

    assert credentials.session.get_secret_value() == SESSION
    assert credentials.api_id == 123456
    assert credentials.api_hash.get_secret_value() == API_HASH
    assert SESSION not in repr(credentials)


def test_missing_value_is_named_without_secrets(tmp_path: Path) -> None:
    path = write(tmp_path, f"session={SESSION}\napi_id=123456\n")

    with pytest.raises(TelegramSecretsFileError) as raised:
        TelegramSecretsFile(path).read()

    assert "api_hash" in str(raised.value)
    assert SESSION not in str(raised.value)


@pytest.mark.parametrize(
    "text",
    [
        f"{SESSION}\napi_id=1\napi_hash={API_HASH}\n",
        f"session={SESSION}\napi_id=abc\napi_hash={API_HASH}\n",
        f"session={SESSION}\nsession={SESSION}\napi_id=1\napi_hash={API_HASH}\n",
    ],
)
def test_malformed_file_is_rejected_without_secrets(tmp_path: Path, text: str) -> None:
    with pytest.raises(TelegramSecretsFileError) as raised:
        TelegramSecretsFile(write(tmp_path, text)).read()

    assert SESSION not in str(raised.value)
    assert API_HASH not in str(raised.value)


def test_client_ignores_updates_and_sleeps_only_short_flood_waits() -> None:
    credentials = TelegramCredentials.model_validate(
        {"session": "", "api_id": 1, "api_hash": API_HASH}
    )

    client = TelethonClientFactory(credentials).create()

    assert client.flood_sleep_threshold == 10
    assert client._no_updates
    assert not client.is_connected()


def test_loop_thread_gives_up_after_timeout() -> None:
    async def never_answers() -> None:
        await asyncio.sleep(10)

    with pytest.raises(TelegramTimeoutError):
        EventLoopThread("test-telegram", 0.05).run(never_answers())
