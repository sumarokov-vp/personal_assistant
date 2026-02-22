from pathlib import Path


class VoiceFileStorage:
    def __init__(self) -> None:
        self._storage: dict[str, Path] = {}

    def _key(self, chat_id: int, message_id: int) -> str:
        return f"{chat_id}:{message_id}"

    def save(self, chat_id: int, message_id: int, file_path: Path) -> None:
        self._storage[self._key(chat_id, message_id)] = file_path

    def get(self, chat_id: int, message_id: int) -> Path | None:
        return self._storage.get(self._key(chat_id, message_id))

    def remove(self, chat_id: int, message_id: int) -> None:
        self._storage.pop(self._key(chat_id, message_id), None)
