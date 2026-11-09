from typing import Protocol


class IProtocolModel(Protocol):
    def ask(self, system: str, prompt: str) -> str: ...
