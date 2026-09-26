from typing import Protocol


class ISystemPromptBuilder(Protocol):
    def build(self) -> str: ...
