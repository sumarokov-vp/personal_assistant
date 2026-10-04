import re
from dataclasses import dataclass
from typing import Self

FIELD_NAME = re.compile(rb"([\x21-\x7e]+?):")
FOLDING_WHITESPACE = (b" ", b"\t")
LINE_ENDINGS = (b"\r\n", b"\n")


@dataclass(frozen=True)
class RawHeaderBlock:
    fields: tuple[tuple[bytes, bytes], ...]
    separator: bytes
    body: bytes

    @classmethod
    def parse(cls, raw: bytes) -> Self | None:
        fields: list[list[bytes]] = []
        lines = raw.splitlines(keepends=True)
        for position, line in enumerate(lines):
            if line in LINE_ENDINGS:
                return cls(
                    fields=tuple((name, field) for name, field in fields),
                    separator=line,
                    body=b"".join(lines[position + 1 :]),
                )
            if line.startswith(FOLDING_WHITESPACE):
                if not fields:
                    return None
                fields[-1][1] += line
                continue
            match = FIELD_NAME.match(line)
            if match is None:
                return None
            fields.append([match.group(1).lower(), line])
        return None

    def header_bytes(self) -> bytes:
        return b"".join(field for _, field in self.fields) + self.separator

    def fields_named(self, name: bytes) -> list[bytes]:
        return [field for field_name, field in self.fields if field_name == name]

    def with_single(self, name: bytes, kept: bytes) -> bytes:
        fields = [
            field
            for field_name, field in self.fields
            if field_name != name or field is kept
        ]
        return b"".join(fields) + self.separator + self.body
