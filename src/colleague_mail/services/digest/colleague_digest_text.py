from collections.abc import Mapping

from src.colleague_mail.models.colleague_message import ColleagueMessage
from src.colleague_mail.models.colleague_message_type import ColleagueMessageType

DIGEST_TITLE = "Почта коллег — непоказанные входящие: {count}"
FIELD_SEPARATOR = " · "

GROUP_TITLES: dict[ColleagueMessageType, str] = {
    ColleagueMessageType.REMARK: "Замечания к общим агентам",
    ColleagueMessageType.QUESTION: "Вопросы",
    ColleagueMessageType.ANSWER: "Ответы",
}


def render_colleague_digest(
    messages: list[ColleagueMessage], names: Mapping[str, str]
) -> str:
    sections = [DIGEST_TITLE.format(count=len(messages))]
    for message_type, title in GROUP_TITLES.items():
        lines = [
            _message_line(message, names)
            for message in messages
            if message.type is message_type
        ]
        if lines:
            sections.append("\n".join([title, *lines]))
    return "\n\n".join(sections)


def _message_line(message: ColleagueMessage, names: Mapping[str, str]) -> str:
    fields = [names.get(message.peer, message.peer)]
    if message.about_agent:
        fields.append(message.about_agent)
    fields.append(message.text)
    return FIELD_SEPARATOR.join(fields)
