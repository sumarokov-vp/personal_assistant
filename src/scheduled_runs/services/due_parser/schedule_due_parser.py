from logging import getLogger

from pydantic import ValidationError

from src.scheduled_runs.services.entities.schedule_due import ScheduleDue

logger = getLogger(__name__)


class ScheduleDueParser:
    def parse(self, raw: bytes) -> ScheduleDue | None:
        try:
            return ScheduleDue.model_validate_json(raw)
        except ValidationError as error:
            logger.warning(
                "Schedule due body does not match format v1: %s",
                error.errors(include_url=False, include_input=False),
            )
            return None
