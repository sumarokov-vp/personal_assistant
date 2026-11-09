from typing import Protocol

from src.flows.recordings.services.entities.callback_button import CallbackButton


class IButtonsSender(Protocol):
    def send_with_buttons(
        self, chat_id: int, text: str, buttons: list[CallbackButton]
    ) -> None: ...
