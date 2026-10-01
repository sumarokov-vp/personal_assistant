from typing import Protocol


class IPromptBuilder(Protocol):
    def build(self) -> str: ...
