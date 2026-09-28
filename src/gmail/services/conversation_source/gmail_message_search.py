from src.conversations.models.message_query import MessageQuery
from src.conversations.models.message_summary import MessageSummary
from src.gmail.services.conversation_source.gmail_search_query import (
    GmailSearchQuery,
)
from src.gmail.services.conversation_source.mail_conversation_mapper import (
    MailConversationMapper,
)
from src.gmail.services.conversation_source.protocols.i_gmail_searcher import (
    IGmailSearcher,
)


class GmailMessageSearch:
    def __init__(self, searcher: IGmailSearcher) -> None:
        self._searcher = searcher
        self._query = GmailSearchQuery()
        self._mapper = MailConversationMapper()

    def search(self, query: MessageQuery) -> list[MessageSummary]:
        if query.conversation_id is not None:
            raise ValueError("Поиск внутри треда Gmail — через GmailConversationSource")
        found = self._searcher.search_messages(self._query.build(query), query.limit)
        return [self._mapper.summary(mail) for mail in found]
