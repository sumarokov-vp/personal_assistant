from dataclasses import dataclass, field

from bot_framework import ParseMode


@dataclass
class SentMessage:
    chat_id: int
    text: str
    parse_mode: ParseMode


@dataclass
class RecordingMessageSender:
    sent: list[SentMessage] = field(default_factory=list)

    def send(self, chat_id: int, text: str, parse_mode: ParseMode) -> object:
        self.sent.append(SentMessage(chat_id=chat_id, text=text, parse_mode=parse_mode))
        return None
