from src.conversations.errors.conversation_source_error import (
    ConversationSourceError,
)


class WhatsAppSchemaError(ConversationSourceError):
    def __init__(self, table: str, missing_columns: list[str]) -> None:
        columns = ", ".join(missing_columns) if missing_columns else "вся таблица"
        super().__init__(
            f"Схема базы WhatsApp не та, что ожидалась: в {table} нет {columns}. "
            "Вероятно, обновился WhatsApp Desktop — чтение снимка нужно поправить "
            "под новую схему"
        )
        self.table = table
        self.missing_columns = missing_columns
