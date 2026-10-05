from typing import Protocol

from workers.knowledge_intake.protocols.i_conversation_answer import (
    IConversationAnswer,
)


class IKnowledgeConversation(Protocol):
    def process_message(
        self, thread_id: str, user_message: str
    ) -> IConversationAnswer: ...
