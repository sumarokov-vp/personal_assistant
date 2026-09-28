from datetime import datetime

from telethon import utils
from telethon.tl.types import Channel, Chat, User

from src.telegram_user.models.telegram_chat import TelegramChat

SAVED_MESSAGES = "Избранное"
DELETED_ACCOUNT = "Удалённый аккаунт"
PUBLIC_LINK_BASE = "https://t.me/{username}"
PRIVATE_SUPERGROUP_LINK_BASE = "https://t.me/c/{channel_id}"


def chat_from_entity(
    entity: object, last_message_at: datetime | None = None
) -> TelegramChat | None:
    if isinstance(entity, User):
        return _chat(entity, user_title(entity), False, None, last_message_at)
    if isinstance(entity, Chat):
        return _chat(entity, entity.title, True, None, last_message_at)
    if isinstance(entity, Channel) and not entity.broadcast:
        return _chat(
            entity, entity.title, True, _supergroup_link_base(entity), last_message_at
        )
    return None


def display_name(entity: object) -> str | None:
    if isinstance(entity, User):
        return user_title(entity)
    if isinstance(entity, Chat | Channel):
        return entity.title
    return None


def public_username(entity: object) -> str | None:
    if not isinstance(entity, User | Channel):
        return None
    if entity.username:
        return entity.username
    for username in entity.usernames or []:
        if username.active:
            return username.username
    return None


def user_title(user: User) -> str:
    if user.is_self:
        return SAVED_MESSAGES
    name = " ".join(part for part in (user.first_name, user.last_name) if part)
    if name:
        return name
    if user.username:
        return f"@{user.username}"
    if user.deleted:
        return DELETED_ACCOUNT
    return f"id {user.id}"


def _supergroup_link_base(channel: Channel) -> str:
    username = public_username(channel)
    if username:
        return PUBLIC_LINK_BASE.format(username=username)
    return PRIVATE_SUPERGROUP_LINK_BASE.format(channel_id=channel.id)


def _chat(
    entity: User | Chat | Channel,
    title: str,
    is_group: bool,
    link_base: str | None,
    last_message_at: datetime | None,
) -> TelegramChat:
    return TelegramChat(
        conversation_id=str(utils.get_peer_id(entity)),
        title=title,
        is_group=is_group,
        link_base=link_base,
        entity=entity,
        last_message_at=last_message_at,
    )
