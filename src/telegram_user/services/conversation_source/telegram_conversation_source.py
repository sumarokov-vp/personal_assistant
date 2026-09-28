from pathlib import Path
from zoneinfo import ZoneInfo

from src.conversations.models.attachment_content import AttachmentContent
from src.conversations.models.conversation import Conversation
from src.conversations.models.conversation_attachment import ConversationAttachment
from src.conversations.models.conversation_message import ConversationMessage
from src.conversations.models.conversation_summary import ConversationSummary
from src.conversations.models.conversation_window import ConversationWindow
from src.conversations.models.message_query import MessageQuery
from src.conversations.models.message_summary import MessageSummary
from src.telegram_user.repos.event_loop_thread import EventLoopThread
from src.telegram_user.repos.telegram_secrets_file import TelegramSecretsFile
from src.telegram_user.repos.telethon_client_factory import TelethonClientFactory
from src.telegram_user.services.attachment_store.telegram_attachment_store import (
    TelegramAttachmentStore,
)
from src.telegram_user.services.conversation_directory.telegram_conversation_directory import (
    TelegramConversationDirectory,
)
from src.telegram_user.services.conversation_reader.telegram_conversation_reader import (
    TelegramConversationReader,
)
from src.telegram_user.services.message_locator.message_locator import (
    MessageLocator,
)
from src.telegram_user.services.message_mapper.message_mapper import MessageMapper
from src.telegram_user.services.message_search.telegram_message_search import (
    TelegramMessageSearch,
)
from src.telegram_user.services.owner_clock.owner_clock import OwnerClock
from src.telegram_user.services.telegram_account.protocols.i_telethon_client_factory import (
    ITelethonClientFactory,
)
from src.telegram_user.services.telegram_account.telegram_account import (
    TelegramAccount,
)

LOOP_THREAD_NAME = "telegram-user"
REQUEST_TIMEOUT_SECONDS = 300.0


class TelegramConversationSource:
    def __init__(
        self,
        client_factory: ITelethonClientFactory,
        timezone: ZoneInfo,
        request_timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._loop = EventLoopThread(LOOP_THREAD_NAME, request_timeout_seconds)
        self._account = TelegramAccount(client_factory)
        clock = OwnerClock(timezone)
        mapper = MessageMapper(clock)
        locator = MessageLocator(self._account)
        self._search = TelegramMessageSearch(self._account, mapper, clock)
        self._reader = TelegramConversationReader(self._account, locator, mapper, clock)
        self._attachments = TelegramAttachmentStore(locator, mapper, self._account)
        self._directory = TelegramConversationDirectory(self._account, clock)

    @classmethod
    def from_secrets_file(
        cls, secrets_file: Path, timezone: ZoneInfo
    ) -> "TelegramConversationSource":
        credentials = TelegramSecretsFile(secrets_file).read()
        return cls(TelethonClientFactory(credentials), timezone)

    def search(self, query: MessageQuery) -> list[MessageSummary]:
        return self._loop.run(self._account.perform(lambda: self._search.search(query)))

    def read_message(self, message_id: str) -> ConversationMessage:
        return self._loop.run(
            self._account.perform(lambda: self._reader.read_message(message_id))
        )

    def read_conversation(
        self, conversation_id: str, window: ConversationWindow
    ) -> Conversation:
        return self._loop.run(
            self._account.perform(
                lambda: self._reader.read_conversation(conversation_id, window)
            )
        )

    def list_attachments(self, message_id: str) -> list[ConversationAttachment]:
        return self._loop.run(
            self._account.perform(
                lambda: self._attachments.list_attachments(message_id)
            )
        )

    def fetch_attachment(
        self, message_id: str, attachment_id: str
    ) -> AttachmentContent:
        return self._loop.run(
            self._account.perform(
                lambda: self._attachments.fetch_attachment(message_id, attachment_id)
            )
        )

    def list_conversations(
        self, title_contains: str | None, limit: int
    ) -> list[ConversationSummary]:
        return self._loop.run(
            self._account.perform(
                lambda: self._directory.list_conversations(title_contains, limit)
            )
        )
