from logging import getLogger

from telebot import TeleBot
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
)

from src.flows.recordings.services.entities.callback_button import CallbackButton

HTML_PARSE_MODE = "HTML"

logger = getLogger(__name__)


class TelegramButtonsSender:
    def __init__(self, bot: TeleBot) -> None:
        self._bot = bot

    def send_with_buttons(
        self, chat_id: int, text: str, buttons: list[CallbackButton]
    ) -> None:
        markup = InlineKeyboardMarkup()
        markup.row(
            *(
                InlineKeyboardButton(text=button.text, callback_data=button.data)
                for button in buttons
            )
        )
        message = self._bot.send_message(
            chat_id,
            text,
            parse_mode=HTML_PARSE_MODE,
            reply_markup=markup,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
        logger.info(
            "Recording outcome sent: chat %d, message_id %d",
            chat_id,
            message.message_id,
        )
