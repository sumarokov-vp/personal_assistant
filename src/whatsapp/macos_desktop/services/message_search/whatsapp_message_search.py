from src.conversations.errors.conversation_not_found_error import (
    ConversationNotFoundError,
)
from src.conversations.models.message_query import MessageQuery
from src.conversations.models.message_summary import MessageSummary
from src.whatsapp.macos_desktop.services.entities.snapshot_key import parse_snapshot_key
from src.whatsapp.macos_desktop.services.message_search.protocols.i_message_finder import (
    IMessageFinder,
)
from src.whatsapp.macos_desktop.services.message_search.protocols.i_moment_converter import (
    IMomentConverter,
)
from src.whatsapp.macos_desktop.services.message_search.protocols.i_summary_mapper import (
    ISummaryMapper,
)


class WhatsAppMessageSearch:
    def __init__(
        self,
        messages: IMessageFinder,
        mapper: ISummaryMapper,
        clock: IMomentConverter,
    ) -> None:
        self._messages = messages
        self._mapper = mapper
        self._clock = clock

    def search(self, query: MessageQuery) -> list[MessageSummary]:
        participant = (query.participant or "").strip()
        rows = self._messages.search(
            text=query.text.strip(),
            chat_pk=self._chat_pk(query.conversation_id),
            participant=participant or None,
            since=None if query.since is None else self._clock.to_seconds(query.since),
            until=None if query.until is None else self._clock.to_seconds(query.until),
            limit=query.limit,
        )
        return [self._mapper.to_summary(row) for row in rows]

    def _chat_pk(self, conversation_id: str | None) -> int | None:
        if conversation_id is None:
            return None
        chat_pk = parse_snapshot_key(conversation_id)
        if chat_pk is None:
            raise ConversationNotFoundError(conversation_id)
        return chat_pk
