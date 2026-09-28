from pathlib import Path

from src.conversations.errors.conversation_source_error import (
    ConversationSourceError,
)


class WhatsAppSnapshotMissingError(ConversationSourceError):
    def __init__(self, database_path: Path) -> None:
        super().__init__(
            f"Снимка WhatsApp нет: {database_path}. Проверь хост-процесс "
            "whatsapp_snapshot (launchd на Mac mini) и монтирование каталога снимка"
        )
        self.database_path = database_path
