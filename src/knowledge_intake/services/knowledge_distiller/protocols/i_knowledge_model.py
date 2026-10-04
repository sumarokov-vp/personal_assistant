from typing import Protocol


class IKnowledgeModel(Protocol):
    def answer(self, thread_id: str, request: str) -> str: ...
