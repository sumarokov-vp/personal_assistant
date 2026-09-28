import os
import secrets
from pathlib import Path

PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


class MediaCache:
    def __init__(self, root: Path) -> None:
        self._root = root

    def find(self, key: str) -> Path | None:
        candidate = self._root / key
        return candidate if candidate.is_file() else None

    def store(self, key: str, content: bytes) -> None:
        self._root.mkdir(mode=PRIVATE_DIR_MODE, parents=True, exist_ok=True)
        partial = self._root / f".{key}.{secrets.token_hex(4)}.part"
        descriptor = os.open(
            partial,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            PRIVATE_FILE_MODE,
        )
        with os.fdopen(descriptor, "wb") as file:
            file.write(content)
        partial.replace(self._root / key)
