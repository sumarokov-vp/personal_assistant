from typing import Protocol

from src.scheduled_runs.services.executor.model_reply import ModelReply


class IRunModel(Protocol):
    def answer(self, thread_id: str, request: str) -> ModelReply: ...
