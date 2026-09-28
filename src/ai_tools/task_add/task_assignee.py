import re

ASSIGNEE_PATTERN = re.compile(r"^(self|assistant|(agent|person|colleague):\S.*)$")
ASSIGNEE_HINT = (
    "Исполнитель — self (сам владелец), assistant (ассистент), agent:<имя>, "
    "person:<имя> или colleague:<пользователь>."
)


def is_known_assignee(assignee: str) -> bool:
    return ASSIGNEE_PATTERN.match(assignee) is not None
