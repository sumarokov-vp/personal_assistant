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
from src.conversations.models.source_freshness import SourceFreshness
from src.whatsapp.macos_desktop.repos.media_cache import MediaCache
from src.whatsapp.macos_desktop.repos.snapshot_database import SnapshotDatabase
from src.whatsapp.macos_desktop.repos.snapshot_marker import SnapshotMarker
from src.whatsapp.macos_desktop.repos.snapshot_schema import SnapshotSchema
from src.whatsapp.macos_desktop.repos.whatsapp_chat_repo import WhatsAppChatRepo
from src.whatsapp.macos_desktop.repos.whatsapp_message_repo import WhatsAppMessageRepo
from src.whatsapp.macos_desktop.services.attachment_describer.attachment_describer import (
    AttachmentDescriber,
)
from src.whatsapp.macos_desktop.services.attachment_store.whatsapp_attachment_store import (
    WhatsAppAttachmentStore,
)
from src.whatsapp.macos_desktop.services.conversation_directory.whatsapp_conversation_directory import (
    WhatsAppConversationDirectory,
)
from src.whatsapp.macos_desktop.services.conversation_reader.whatsapp_conversation_reader import (
    WhatsAppConversationReader,
)
from src.whatsapp.macos_desktop.services.core_data_clock.core_data_clock import (
    CoreDataClock,
)
from src.whatsapp.macos_desktop.services.freshness.whatsapp_freshness import (
    WhatsAppFreshness,
)
from src.whatsapp.macos_desktop.services.message_mapper.message_mapper import (
    MessageMapper,
)
from src.whatsapp.macos_desktop.services.conversation_source.protocols.i_cdn_client import (
    ICdnClient,
)
from src.whatsapp.macos_desktop.services.conversation_source.protocols.i_document_fallback import (
    IDocumentFallback,
)
from src.whatsapp.macos_desktop.services.media_cipher.media_cipher import (
    WhatsAppMediaCipher,
)
from src.whatsapp.macos_desktop.services.message_search.whatsapp_message_search import (
    WhatsAppMessageSearch,
)
from src.whatsapp.macos_desktop.services.remote_media.remote_media import (
    WhatsAppRemoteMedia,
)

DATABASE_FILE = "ChatStorage.sqlite"
MEDIA_ROOT = "Message"
SNAPSHOT_MARKER = "snapshot_at"


class WhatsAppConversationSource:
    def __init__(
        self,
        snapshot_dir: Path,
        timezone: ZoneInfo,
        media_cache_dir: Path,
        cdn_client: ICdnClient,
        document_fallback: IDocumentFallback | None = None,
    ) -> None:
        database = SnapshotDatabase(snapshot_dir / DATABASE_FILE, SnapshotSchema())
        messages = WhatsAppMessageRepo(database)
        chats = WhatsAppChatRepo(database)
        clock = CoreDataClock(timezone)
        remote_media = WhatsAppRemoteMedia(
            MediaCache(media_cache_dir),
            cdn_client,
            WhatsAppMediaCipher(),
            fallback=document_fallback,
        )
        describer = AttachmentDescriber(snapshot_dir / MEDIA_ROOT, remote_media)
        mapper = MessageMapper(clock, describer)
        self._search = WhatsAppMessageSearch(messages, mapper, clock)
        self._reader = WhatsAppConversationReader(messages, chats, mapper, clock)
        self._attachments = WhatsAppAttachmentStore(messages, describer, remote_media)
        self._directory = WhatsAppConversationDirectory(chats, clock)
        self._freshness = WhatsAppFreshness(
            messages, SnapshotMarker(snapshot_dir / SNAPSHOT_MARKER), clock
        )

    def search(self, query: MessageQuery) -> list[MessageSummary]:
        return self._search.search(query)

    def read_message(self, message_id: str) -> ConversationMessage:
        return self._reader.read_message(message_id)

    def read_conversation(
        self, conversation_id: str, window: ConversationWindow
    ) -> Conversation:
        return self._reader.read_conversation(conversation_id, window)

    def list_attachments(self, message_id: str) -> list[ConversationAttachment]:
        return self._attachments.list_attachments(message_id)

    def fetch_attachment(
        self, message_id: str, attachment_id: str
    ) -> AttachmentContent:
        return self._attachments.fetch_attachment(message_id, attachment_id)

    def list_conversations(
        self, title_contains: str | None, limit: int
    ) -> list[ConversationSummary]:
        return self._directory.list_conversations(title_contains, limit)

    def freshness(self) -> SourceFreshness:
        return self._freshness.freshness()
