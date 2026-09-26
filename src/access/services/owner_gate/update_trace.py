from dataclasses import dataclass

from telebot.types import Update

UNKNOWN_KIND = "unknown"


@dataclass(frozen=True)
class UpdateTrace:
    kind: str
    from_id: int | None
    chat_id: int | None

    @classmethod
    def of(cls, update: Update) -> "UpdateTrace":
        kind, payload = cls._payload(update)
        return cls(
            kind=kind,
            from_id=cls._from_id(payload),
            chat_id=cls._chat_id(payload),
        )

    @staticmethod
    def _payload(update: Update) -> tuple[str, object]:
        for kind, payload in vars(update).items():
            if kind != "update_id" and payload is not None:
                return kind, payload
        return UNKNOWN_KIND, None

    @staticmethod
    def _from_id(payload: object) -> int | None:
        sender = getattr(payload, "from_user", None) or getattr(payload, "user", None)
        sender_id = getattr(sender, "id", None)
        return sender_id if isinstance(sender_id, int) else None

    @staticmethod
    def _chat_id(payload: object) -> int | None:
        chat = getattr(payload, "chat", None)
        if chat is None:
            chat = getattr(getattr(payload, "message", None), "chat", None)
        chat_id = getattr(chat, "id", None)
        return chat_id if isinstance(chat_id, int) else None
