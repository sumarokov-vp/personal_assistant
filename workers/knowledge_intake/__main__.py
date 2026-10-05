from logging import getLogger
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

from bot_framework.platform.telegram import TelegramMessageCore
from workers.knowledge_intake.composition import (
    KNOWLEDGE_INTAKE_PROMPT_PATH,
    run_knowledge_intake,
)
from workers.knowledge_intake.knowledge_intake_env import (
    read_knowledge_intake_env,
    require_env,
)
from workers.memory_fill.__main__ import configure_logging
from workers.memory_fill.owner_notifier import OwnerNotifier

logger = getLogger(__name__)


def build_owner_notifier() -> OwnerNotifier:
    core = TelegramMessageCore(bot_token=require_env("BOT_TOKEN"))
    return OwnerNotifier(
        sender=core.message_sender,
        owner_chat_id=int(require_env("OWNER_TELEGRAM_ID")),
    )


def main(notifier: OwnerNotifier) -> None:
    run_knowledge_intake(
        read_knowledge_intake_env(),
        KNOWLEDGE_INTAKE_PROMPT_PATH.read_text(encoding="utf-8"),
        notifier,
    )


if __name__ == "__main__":
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")
    configure_logging(getenv("LOG_LEVEL", "INFO"))
    owner_notifier = build_owner_notifier()
    try:
        main(owner_notifier)
    except Exception as error:
        logger.exception("knowledge_intake run failed")
        owner_notifier.notify(f"Приёмщик знаний не отработал: {type(error).__name__}")
        raise
