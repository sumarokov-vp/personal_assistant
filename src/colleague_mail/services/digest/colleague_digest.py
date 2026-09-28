from logging import getLogger

from src.colleague_mail.models.colleague_message import ColleagueMessage
from src.colleague_mail.services.digest.colleague_digest_text import (
    render_colleague_digest,
)
from src.colleague_mail.services.digest.protocols.i_colleague_finder import (
    IColleagueFinder,
)
from src.colleague_mail.services.digest.protocols.i_owner_notifier import (
    IOwnerNotifier,
)
from src.colleague_mail.services.digest.protocols.i_text_splitter import (
    ITextSplitter,
)
from src.colleague_mail.services.digest.protocols.i_unshown_mail_journal import (
    IUnshownMailJournal,
)

logger = getLogger(__name__)


class ColleagueDigest:
    def __init__(
        self,
        journal: IUnshownMailJournal,
        directory: IColleagueFinder | None,
        notifier: IOwnerNotifier,
        splitter: ITextSplitter,
    ) -> None:
        self._journal = journal
        self._directory = directory
        self._notifier = notifier
        self._splitter = splitter

    def send(self) -> int:
        messages = self._journal.unshown_incoming(
            peer=None, message_type=None, limit=None
        )
        if not messages:
            logger.info("Colleague digest: nothing unshown, not sent")
            return 0
        text = render_colleague_digest(messages, self._names(messages))
        for chunk in self._splitter.split(text):
            self._notifier.notify(chunk)
        self._journal.mark_shown([message.id for message in messages])
        logger.info("Colleague digest sent: %d messages", len(messages))
        return len(messages)

    def _names(self, messages: list[ColleagueMessage]) -> dict[str, str]:
        if self._directory is None:
            return {}
        names: dict[str, str] = {}
        for peer in {message.peer for message in messages}:
            colleague = self._directory.find(peer)
            if colleague is not None:
                names[peer] = colleague.name
        return names
