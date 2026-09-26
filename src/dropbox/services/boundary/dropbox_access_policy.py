import unicodedata
from collections.abc import Sequence

HIDDEN_TOP_LEVEL = ("vault",)
HIDDEN_TOP_LEVEL_PREFIXES = ("vault_selftest_",)
HIDDEN_SUBTREES = (("03_home", "07_ecp", "egov.kz"),)
KEY_FILE_SUFFIXES = (".p12", ".pfx", ".key", ".pem", ".jks", ".gpg")
IMMOVABLE_TOP_LEVEL = ("apps",)


class DropboxAccessPolicy:
    def is_hidden(self, parts: Sequence[str]) -> bool:
        normalized = [_normalize(part) for part in parts]
        if not normalized:
            return False
        if any(part.startswith(".") for part in normalized):
            return True
        top = normalized[0]
        if top in HIDDEN_TOP_LEVEL or top.startswith(HIDDEN_TOP_LEVEL_PREFIXES):
            return True
        return any(
            tuple(normalized[: len(subtree)])
            == tuple(_normalize(part) for part in subtree)
            for subtree in HIDDEN_SUBTREES
        )

    def is_immovable(self, parts: Sequence[str]) -> bool:
        return bool(parts) and _normalize(parts[0]) in IMMOVABLE_TOP_LEVEL

    def is_key_file(self, name: str) -> bool:
        return _normalize(name).endswith(KEY_FILE_SUFFIXES)


def _normalize(part: str) -> str:
    return unicodedata.normalize("NFC", part).casefold()
