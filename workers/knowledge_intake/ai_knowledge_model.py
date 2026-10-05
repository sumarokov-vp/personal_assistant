from workers.knowledge_intake.protocols.i_knowledge_conversation import (
    IKnowledgeConversation,
)


class AiKnowledgeModel:
    def __init__(self, conversation: IKnowledgeConversation) -> None:
        self._conversation = conversation

    def answer(self, thread_id: str, request: str) -> str:
        return self._conversation.process_message(thread_id, request).content or ""
