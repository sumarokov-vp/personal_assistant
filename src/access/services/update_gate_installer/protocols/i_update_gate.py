from typing import Protocol

from telebot.types import Update


class IUpdateGate(Protocol):
    def admitted(self, updates: list[Update]) -> list[Update]: ...
