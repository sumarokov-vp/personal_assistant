from logging import getLogger

from pydantic import ValidationError

from src.colleague_mail.services.entities.mail_body import MailBody

logger = getLogger(__name__)


class MailBodyParser:
    def parse(self, raw: bytes) -> MailBody | None:
        try:
            return MailBody.model_validate_json(raw)
        except ValidationError as error:
            logger.warning(
                "Colleague mail body does not match format v1: %s",
                error.errors(include_url=False, include_input=False),
            )
            return None
