SEPARATOR = ":"


def message_key(conversation_id: str, message_number: int) -> str:
    return f"{conversation_id}{SEPARATOR}{message_number}"


def parse_message_key(message_id: str) -> tuple[str, int] | None:
    conversation_id, separator, number = message_id.strip().rpartition(SEPARATOR)
    if not separator or not conversation_id or not number.isdigit():
        return None
    return conversation_id, int(number)
