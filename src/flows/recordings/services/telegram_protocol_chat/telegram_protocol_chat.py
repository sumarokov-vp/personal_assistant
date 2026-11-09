from io import BytesIO
from logging import getLogger

from telebot import TeleBot
from telebot.types import InputFile, LinkPreviewOptions

HTML_PARSE_MODE = "HTML"

logger = getLogger(__name__)


class TelegramProtocolChat:
    def __init__(self, bot: TeleBot) -> None:
        self._bot = bot

    def send_html(self, chat_id: int, text: str) -> int:
        message = self._bot.send_message(
            chat_id,
            text,
            parse_mode=HTML_PARSE_MODE,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
        logger.info(
            "Protocol message sent: chat %d, message_id %d", chat_id, message.message_id
        )
        return message.message_id

    def send_pdf(self, chat_id: int, file_name: str, pdf: bytes, caption: str) -> int:
        message = self._bot.send_document(
            chat_id,
            InputFile(BytesIO(pdf), file_name=file_name),
            caption=caption,
            parse_mode=HTML_PARSE_MODE,
        )
        logger.info(
            "Protocol PDF sent: chat %d, message_id %d", chat_id, message.message_id
        )
        return message.message_id
