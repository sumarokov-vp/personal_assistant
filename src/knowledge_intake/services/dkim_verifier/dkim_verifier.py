from collections.abc import Callable

import dkim

from src.knowledge_intake.services.entities.dkim_result import DkimResult
from src.knowledge_intake.services.entities.raw_header_block import RawHeaderBlock

SIGNATURE_FIELD = b"dkim-signature"
DOMAIN_TAG = b"d"

type TxtLookup = Callable[..., bytes | None]


class DkimVerifier:
    def __init__(self, txt_lookup: TxtLookup | None = None) -> None:
        self._txt_lookup = txt_lookup

    def check(self, raw: bytes, domain: str) -> DkimResult:
        block = RawHeaderBlock.parse(raw)
        if block is None:
            return DkimResult.INVALID
        signatures = block.fields_named(SIGNATURE_FIELD)
        if not signatures:
            return DkimResult.NO_SIGNATURE
        own = [
            field for field in signatures if _signing_domain(field) == domain.lower()
        ]
        if not own:
            return DkimResult.OTHER_DOMAIN
        if any(
            self._verifies(block.with_single(SIGNATURE_FIELD, field)) for field in own
        ):
            return DkimResult.SIGNED
        return DkimResult.INVALID

    def _verifies(self, message: bytes) -> bool:
        if self._txt_lookup is None:
            return bool(dkim.verify(message))
        return bool(dkim.verify(message, dnsfunc=self._txt_lookup))


def _signing_domain(field: bytes) -> str:
    tag_list = field.partition(b":")[2]
    domains = [
        value.strip()
        for name, _, value in (tag.partition(b"=") for tag in tag_list.split(b";"))
        if name.strip() == DOMAIN_TAG
    ]
    if len(domains) != 1:
        return ""
    unfolded = b"".join(domains[0].split())
    return unfolded.decode("ascii", errors="replace").lower().rstrip(".")
