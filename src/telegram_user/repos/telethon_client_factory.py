from telethon import TelegramClient
from telethon.sessions import StringSession

from src.telegram_user.models.telegram_credentials import TelegramCredentials

FLOOD_SLEEP_THRESHOLD_SECONDS = 10


class TelethonClientFactory:
    def __init__(self, credentials: TelegramCredentials) -> None:
        self._credentials = credentials

    def create(self) -> TelegramClient:
        return TelegramClient(
            StringSession(self._credentials.session.get_secret_value()),
            self._credentials.api_id,
            self._credentials.api_hash.get_secret_value(),
            receive_updates=False,
            flood_sleep_threshold=FLOOD_SLEEP_THRESHOLD_SECONDS,
        )
