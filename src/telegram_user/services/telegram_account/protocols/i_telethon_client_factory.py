from typing import Protocol

from src.telegram_user.services.telegram_account.protocols.i_telethon_client import (
    ITelethonClient,
)


class ITelethonClientFactory(Protocol):
    def create(self) -> ITelethonClient: ...
