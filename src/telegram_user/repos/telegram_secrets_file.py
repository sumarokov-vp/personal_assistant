from pathlib import Path

from pydantic import SecretStr

from src.telegram_user.errors.telegram_secrets_file_error import (
    TelegramSecretsFileError,
)
from src.telegram_user.models.telegram_credentials import TelegramCredentials

SESSION_KEY = "session"
API_ID_KEY = "api_id"
API_HASH_KEY = "api_hash"
KNOWN_KEYS = (SESSION_KEY, API_ID_KEY, API_HASH_KEY)
SEPARATOR = "="


class TelegramSecretsFile:
    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> TelegramCredentials:
        values = self._values()
        missing = [key for key in KNOWN_KEYS if not values.get(key)]
        if missing:
            raise TelegramSecretsFileError(
                self._path, f"нет значений: {', '.join(missing)}"
            )
        if not values[API_ID_KEY].isdigit():
            raise TelegramSecretsFileError(self._path, "api_id должен быть числом")
        return TelegramCredentials(
            session=SecretStr(values[SESSION_KEY]),
            api_id=int(values[API_ID_KEY]),
            api_hash=SecretStr(values[API_HASH_KEY]),
        )

    def _values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        lines = self._path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            key, separator, value = line.partition(SEPARATOR)
            key = key.strip()
            if not separator or key not in KNOWN_KEYS:
                raise TelegramSecretsFileError(
                    self._path,
                    f"строка {number} — не «ключ=значение» с ключом из {', '.join(KNOWN_KEYS)}",
                )
            if key in values:
                raise TelegramSecretsFileError(self._path, f"ключ {key} повторяется")
            values[key] = value.strip()
        return values
