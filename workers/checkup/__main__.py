from logging import getLogger
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

from workers.checkup.checkup_env import read_checkup_env
from workers.checkup.composition import CHECKUP_PROMPT_PATH, run_checkup
from workers.checkup.report_delivery import ReportDelivery
from workers.memory_fill.__main__ import build_owner_notifier, configure_logging
from workers.memory_fill.composition import MEMORY_FILL_PROMPT_PATH
from workers.memory_fill.owner_notifier import OwnerNotifier

logger = getLogger(__name__)


def main(notifier: OwnerNotifier) -> None:
    report = run_checkup(
        read_checkup_env(),
        MEMORY_FILL_PROMPT_PATH.read_text(encoding="utf-8"),
        CHECKUP_PROMPT_PATH.read_text(encoding="utf-8"),
    )
    logger.info("Checkup finished:\n%s", report.render())
    ReportDelivery(notifier).deliver(report)


if __name__ == "__main__":
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")
    configure_logging(getenv("LOG_LEVEL", "INFO"))
    owner_notifier = build_owner_notifier()
    try:
        main(owner_notifier)
    except Exception as error:
        logger.exception("Checkup failed")
        owner_notifier.notify(f"Чекап не завершился: {type(error).__name__}")
        raise
