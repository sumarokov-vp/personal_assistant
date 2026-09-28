from src.conversations.models.attachment_content import AttachmentContent
from src.conversations.models.conversation import Conversation
from src.conversations.models.conversation_attachment import ConversationAttachment
from src.conversations.models.conversation_message import ConversationMessage
from src.conversations.models.conversation_window import ConversationWindow
from src.conversations.models.message_query import MessageQuery
from src.conversations.models.message_summary import MessageSummary
from src.gmail.models.mail_message import MailMessage
from src.gmail.services.conversation_source.as_utc import as_utc
from src.gmail.services.conversation_source.gmail_message_reader import (
    GmailMessageReader,
)
from src.gmail.services.conversation_source.gmail_message_search import (
    GmailMessageSearch,
)
from src.gmail.services.conversation_source.gmail_search_query import (
    GmailSearchQuery,
)
from src.gmail.services.conversation_source.mail_conversation_mapper import (
    MailConversationMapper,
)
from src.gmail.services.conversation_source.protocols.i_gmail_mailbox import (
    IGmailMailbox,
)


class GmailConversationSource:
    def __init__(self, mailbox: IGmailMailbox) -> None:
        self._mailbox = mailbox
        self._search = GmailMessageSearch(mailbox)
        self._reader = GmailMessageReader(mailbox)
        self._query = GmailSearchQuery()
        self._mapper = MailConversationMapper()

    def search(self, query: MessageQuery) -> list[MessageSummary]:
        if query.conversation_id is None:
            return self._search.search(query)
        return self._search_in_thread(query.conversation_id, query)

    def read_message(self, message_id: str) -> ConversationMessage:
        return self._reader.read_message(message_id)

    def read_conversation(
        self, conversation_id: str, window: ConversationWindow
    ) -> Conversation:
        thread = self._mailbox.get_thread(conversation_id)
        in_window = [mail for mail in thread if _within(mail, window)]
        shown = in_window[-window.limit :]
        return Conversation(
            conversation_id=conversation_id,
            title=thread[0].subject if thread else "",
            is_group=False,
            messages=[self._mapper.message(mail) for mail in shown],
            has_earlier=len(shown) < len(in_window)
            or any(_before(mail, window) for mail in thread),
        )

    def list_attachments(self, message_id: str) -> list[ConversationAttachment]:
        return self.read_message(message_id).attachments

    def fetch_attachment(
        self, message_id: str, attachment_id: str
    ) -> AttachmentContent:
        file = self._mailbox.get_attachment_file(message_id, attachment_id)
        return AttachmentContent(
            content=file.content,
            name=file.attachment.filename,
            media_type=file.attachment.media_type,
        )

    def _search_in_thread(
        self, thread_id: str, query: MessageQuery
    ) -> list[MessageSummary]:
        thread = self._mailbox.get_thread(thread_id)
        gmail_query = self._query.build(query)
        if gmail_query:
            matching = self._mailbox.search_thread_message_ids(thread_id, gmail_query)
            thread = [mail for mail in thread if mail.id in matching]
        newest_first = list(reversed(thread))[: query.limit]
        return [self._mapper.summary_of_message(mail) for mail in newest_first]


def _before(mail: MailMessage, window: ConversationWindow) -> bool:
    return (
        window.since is not None
        and mail.received_at is not None
        and mail.received_at < as_utc(window.since)
    )


def _after(mail: MailMessage, window: ConversationWindow) -> bool:
    return (
        window.until is not None
        and mail.received_at is not None
        and mail.received_at > as_utc(window.until)
    )


def _within(mail: MailMessage, window: ConversationWindow) -> bool:
    return not _before(mail, window) and not _after(mail, window)
