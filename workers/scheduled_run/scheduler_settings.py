from dataclasses import dataclass
from logging import getLogger
from os import getenv

logger = getLogger(__name__)

SCHEDULER_ACCOUNT = "scheduler"


@dataclass(frozen=True)
class SchedulerSettings:
    amqp_url: str
    queue: str
    scheduler_account: str = SCHEDULER_ACCOUNT


def read_scheduler_settings() -> SchedulerSettings | None:
    amqp_url = getenv("SCHEDULER_AMQP_URL")
    queue = getenv("SCHEDULER_QUEUE")
    if not amqp_url and not queue:
        logger.info(
            "SCHEDULER_AMQP_URL and SCHEDULER_QUEUE are not set, scheduled runs are off"
        )
        return None
    if not amqp_url or not queue:
        raise ValueError("SCHEDULER_AMQP_URL and SCHEDULER_QUEUE are required together")
    return SchedulerSettings(amqp_url=amqp_url, queue=queue)
