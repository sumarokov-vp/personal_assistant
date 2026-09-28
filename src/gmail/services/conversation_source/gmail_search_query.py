from src.conversations.models.message_query import MessageQuery
from src.gmail.services.conversation_source.as_utc import as_utc


class GmailSearchQuery:
    def build(self, query: MessageQuery) -> str:
        terms = [query.text] if query.text.strip() else []
        if query.participant:
            terms.append(f"from:{_quoted(query.participant)}")
        if query.since is not None:
            terms.append(f"after:{int(as_utc(query.since).timestamp())}")
        if query.until is not None:
            terms.append(f"before:{int(as_utc(query.until).timestamp())}")
        return " ".join(terms)


def _quoted(value: str) -> str:
    if any(character.isspace() for character in value):
        return '"' + value.replace('"', "") + '"'
    return value
