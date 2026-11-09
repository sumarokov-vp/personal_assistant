from logging import getLogger

from telebot import TeleBot
from telebot.types import Message

HTML_PARSE_MODE = "HTML"

logger = getLogger(__name__)


class TeleBotTextSender:
    def __init__(self, bot: TeleBot) -> None:
        self._bot = bot

    def send(self, chat_id: int, text: str) -> Message:
        message = self._bot.send_message(chat_id, text, parse_mode=HTML_PARSE_MODE)
        logger.info(
            "Recording outcome sent: chat %d, message_id %d",
            chat_id,
            message.message_id,
        )
        return message
