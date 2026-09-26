from dataclasses import dataclass


@dataclass(frozen=True)
class AlbumPhoto:
    message_id: int
    user_id: int
    caption: str
    data: bytes
