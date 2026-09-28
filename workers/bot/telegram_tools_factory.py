from logging import getLogger
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_framework import BaseTool

from src.ai_tools.list_telegram_chats import ListTelegramChatsTool
from src.ai_tools.read_telegram import ReadTelegramTool
from src.ai_tools.search_telegram import SearchTelegramTool
from src.ai_tools.telegram_common import UntrustedTelegramFrame
from src.telegram_user.services.conversation_source.telegram_conversation_source import (
    TelegramConversationSource,
)
from workers.bot.protocols.i_telegram_source import ITelegramSource

TELEGRAM_USER_SECRETS_VARIABLE = "TELEGRAM_USER_SECRETS_FILE"

logger = getLogger(__name__)


def build_telegram_source(
    secrets_file: str | None, timezone: ZoneInfo
) -> ITelegramSource | None:
    if not secrets_file:
        logger.info(
            "%s is not set: Telegram tools are off", TELEGRAM_USER_SECRETS_VARIABLE
        )
        return None
    path = Path(secrets_file)
    if not path.is_file():
        logger.info(
            "%s points to a missing file: Telegram tools are off",
            TELEGRAM_USER_SECRETS_VARIABLE,
        )
        return None
    return TelegramConversationSource.from_secrets_file(path, timezone)


def build_telegram_tools(source: ITelegramSource, timezone: ZoneInfo) -> list[BaseTool]:
    frame = UntrustedTelegramFrame()
    return [
        SearchTelegramTool(searcher=source, frame=frame, timezone=timezone),
        ReadTelegramTool(reader=source, frame=frame, timezone=timezone),
        ListTelegramChatsTool(directory=source, frame=frame),
    ]
