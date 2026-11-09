from typing import Protocol

from src.flows.recordings.services.entities.url_button import UrlButton


class IUrlButtonsSender(Protocol):
    def send_with_url_buttons(
        self, chat_id: int, text: str, buttons: list[UrlButton]
    ) -> None: ...
