from src.protocols.models.discussion_topic import DiscussionTopic
from src.protocols.models.protocol_action import ProtocolAction
from src.protocols.models.protocol_content import ProtocolContent
from src.protocols.models.protocol_kind import ProtocolKind
from src.protocols.services.telegram_protocol_text import TelegramProtocolText


def _meeting(points: int) -> ProtocolContent:
    return ProtocolContent(
        kind=ProtocolKind.MEETING,
        title="Клиент <A&B>: сроки",
        date="09.11.2026",
        parties={"Smartist": ["Владелец"]},
        agenda=["Сроки"],
        discussion=[
            DiscussionTopic(
                topic="Сроки",
                points=[
                    f"Тезис номер {number} про поставку" for number in range(points)
                ],
            )
        ],
        agreements=["Поставка до пятницы"],
        actions=[ProtocolAction(what="Отгрузить", who="Подрядчик")],
        open_questions=["Кто принимает"],
    )


def test_short_protocol_is_one_message_with_escaped_text() -> None:
    [message] = TelegramProtocolText().messages(_meeting(points=3))

    assert message.startswith(
        "<b>Протокол встречи</b>\n<i>Клиент &lt;A&amp;B&gt;: сроки</i>"
    )
    assert "1. Отгрузить — <b>Подрядчик</b>" in message
    assert "срок" not in message.split("Поручения")[1].split("\n")[1]


def test_long_protocol_splits_on_section_borders_within_limit() -> None:
    limit = 400
    messages = TelegramProtocolText(max_chars=limit).messages(_meeting(points=40))

    assert len(messages) > 2
    assert all(len(message) <= limit for message in messages)
    joined = "\n".join(messages)
    assert all(f"Тезис номер {number} про" in joined for number in range(40))
    assert "<b>Обсуждение (продолжение)</b>" in joined
    assert messages[-1].endswith("• Кто принимает")
    assert all(message.startswith("<b>") for message in messages)
