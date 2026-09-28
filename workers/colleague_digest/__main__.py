from logging import getLogger
from os import getenv
from pathlib import Path

from bot_framework.platform.telegram import TelegramMessageCore
from dotenv import load_dotenv

from src.colleague_mail.services.digest.protocols.i_owner_notifier import (
    IOwnerNotifier,
)
from workers.colleague_digest.composition import build_colleague_digest
from workers.memory_fill.__main__ import configure_logging
from workers.memory_fill.memory_fill_env import require_env
from workers.memory_fill.owner_notifier import OwnerNotifier

logger = getLogger(__name__)


def build_owner_notifier() -> OwnerNotifier:
    core = TelegramMessageCore(bot_token=require_env("BOT_TOKEN"))
    return OwnerNotifier(
        sender=core.message_sender,
        owner_chat_id=int(require_env("OWNER_TELEGRAM_ID")),
    )


def main(notifier: IOwnerNotifier) -> None:
    directory_file = getenv("ASSISTANT_DIRECTORY_FILE")
    digest = build_colleague_digest(
        database_url=require_env("BOT_DB_URL"),
        directory_file=Path(directory_file) if directory_file else None,
        notifier=notifier,
    )
    logger.info("Colleague digest: %d messages shown", digest.send())


if __name__ == "__main__":
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")
    configure_logging(getenv("LOG_LEVEL", "INFO"))
    try:
        main(build_owner_notifier())
    except Exception:
        logger.exception("Colleague digest failed")
        raise
