from typing import Protocol


class IMediaCipher(Protocol):
    def decrypt(
        self, encrypted: bytes, media_key: bytes, key_info: bytes
    ) -> bytes | None: ...
