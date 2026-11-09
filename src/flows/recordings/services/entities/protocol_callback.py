import re

from src.flows.recordings.services.entities.callback_button import CallbackButton
from src.protocols.models.protocol_kind import ProtocolKind

PROTOCOL_CALLBACK_PREFIX = "prt:"
KIND_CODES = {ProtocolKind.MEETING: "m", ProtocolKind.CALL: "c"}
KIND_BY_CODE = {code: kind for kind, code in KIND_CODES.items()}
BUTTON_TITLES = {
    ProtocolKind.MEETING: "Протокол встречи",
    ProtocolKind.CALL: "Протокол звонка",
}
CALLBACK_PATTERN = re.compile(r"^prt:([mc]):([0-9a-f]{8})$")


class ProtocolCallback:
    prefix = PROTOCOL_CALLBACK_PREFIX

    def buttons(self, transcript_id: str) -> list[CallbackButton]:
        return [
            CallbackButton(
                text=BUTTON_TITLES[kind], data=self.data(kind, transcript_id)
            )
            for kind in (ProtocolKind.MEETING, ProtocolKind.CALL)
        ]

    def data(self, kind: ProtocolKind, transcript_id: str) -> str:
        return f"{self.prefix}{KIND_CODES[kind]}:{transcript_id}"

    def parse(self, data: str | None) -> tuple[ProtocolKind, str] | None:
        match = CALLBACK_PATTERN.match(data or "")
        if match is None:
            return None
        return KIND_BY_CODE[match.group(1)], match.group(2)
