from src.conversations.errors.conversation_not_found_error import (
    ConversationNotFoundError,
)
from src.conversations.errors.message_not_found_error import MessageNotFoundError
from src.conversations.models.conversation import Conversation
from src.conversations.models.conversation_message import ConversationMessage
from src.conversations.models.conversation_window import ConversationWindow
from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow
from src.whatsapp.macos_desktop.services.conversation_reader.protocols.i_chat_lookup import (
    IChatLookup,
)
from src.whatsapp.macos_desktop.services.conversation_reader.protocols.i_chat_message_rows import (
    IChatMessageRows,
)
from src.whatsapp.macos_desktop.services.conversation_reader.protocols.i_message_mapper import (
    IMessageMapper,
)
from src.whatsapp.macos_desktop.services.conversation_reader.protocols.i_moment_converter import (
    IMomentConverter,
)
from src.whatsapp.macos_desktop.services.entities.chat_title import (
    chat_title,
    is_group_session,
)
from src.whatsapp.macos_desktop.services.entities.snapshot_key import parse_snapshot_key

BEFORE_ANY_MESSAGE = 0


class WhatsAppConversationReader:
    def __init__(
        self,
        messages: IChatMessageRows,
        chats: IChatLookup,
        mapper: IMessageMapper,
        clock: IMomentConverter,
    ) -> None:
        self._messages = messages
        self._chats = chats
        self._mapper = mapper
        self._clock = clock

    def read_message(self, message_id: str) -> ConversationMessage:
        message_pk = parse_snapshot_key(message_id)
        row = None if message_pk is None else self._messages.by_pk(message_pk)
        if row is None:
            raise MessageNotFoundError(message_id)
        return self._mapper.to_message(row)

    def read_conversation(
        self, conversation_id: str, window: ConversationWindow
    ) -> Conversation:
        chat_pk = parse_snapshot_key(conversation_id)
        chat = None if chat_pk is None else self._chats.by_pk(chat_pk)
        if chat is None:
            raise ConversationNotFoundError(conversation_id)
        since = None if window.since is None else self._clock.to_seconds(window.since)
        until = None if window.until is None else self._clock.to_seconds(window.until)
        rows = self._messages.in_chat(chat.chat_pk, since, until, window.limit)
        return Conversation(
            conversation_id=str(chat.chat_pk),
            title=chat_title(chat.title, chat.jid, chat.chat_pk),
            is_group=is_group_session(chat.session_type),
            messages=[self._mapper.to_message(row) for row in rows],
            has_earlier=self._has_earlier(chat.chat_pk, rows, since),
        )

    def _has_earlier(
        self, chat_pk: int, rows: list[WhatsAppMessageRow], since: float | None
    ) -> bool:
        if rows and rows[0].sent_at is not None:
            return self._messages.has_before(
                chat_pk, rows[0].sent_at, rows[0].message_pk
            )
        if not rows and since is not None:
            return self._messages.has_before(chat_pk, since, BEFORE_ANY_MESSAGE)
        return False
