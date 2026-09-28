GROUP_SESSION_TYPE = 1


def chat_title(name: str | None, jid: str | None, chat_pk: int) -> str:
    if name:
        return name
    if jid:
        return jid.split("@", 1)[0]
    return f"чат {chat_pk}"


def is_group_session(session_type: int | None) -> bool:
    return session_type == GROUP_SESSION_TYPE
