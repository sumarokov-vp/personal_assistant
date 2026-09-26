from logging import WARNING, basicConfig, getLogger
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

from bot_framework.platform.telegram import TelegramMessageCore
from workers.memory_fill.composition import MEMORY_FILL_PROMPT_PATH, run_memory_fill
from workers.memory_fill.memory_fill_env import read_memory_fill_env, require_env
from workers.memory_fill.owner_notifier import OwnerNotifier

logger = getLogger(__name__)

TOKEN_LEAKING_LOGGERS = ["TeleBot", "urllib3", "requests", "httpx", "anthropic"]


def configure_logging(level: str) -> None:
    basicConfig(level=level.upper())
    for name in TOKEN_LEAKING_LOGGERS:
        getLogger(name).setLevel(WARNING)


def build_owner_notifier() -> OwnerNotifier:
    core = TelegramMessageCore(bot_token=require_env("BOT_TOKEN"))
    return OwnerNotifier(
        sender=core.message_sender, owner_chat_id=int(require_env("OWNER_CHAT_ID"))
    )


def main(notifier: OwnerNotifier) -> None:
    report = run_memory_fill(
        read_memory_fill_env(), MEMORY_FILL_PROMPT_PATH.read_text(encoding="utf-8")
    )
    text = report.render()
    print(text)  # noqa: T201
    notifier.notify(text)


if __name__ == "__main__":
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")
    configure_logging(getenv("LOG_LEVEL", "INFO"))
    owner_notifier = build_owner_notifier()
    try:
        main(owner_notifier)
    except Exception as error:
        logger.exception("Memory fill failed")
        owner_notifier.notify(
            f"Наполнение памяти не завершилось: {type(error).__name__}"
        )
        raise
