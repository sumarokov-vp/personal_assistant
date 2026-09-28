from collections.abc import Sequence
from typing import ClassVar

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, Field

from src.ai_tools.colleague_mail.colleague_message_kind import ColleagueMessageKind
from src.ai_tools.colleague_mail.colleague_send.protocols.i_colleague_directory import (
    IColleagueDirectory,
)
from src.ai_tools.colleague_mail.colleague_send.protocols.i_colleague_mail_gateway import (
    IColleagueMailGateway,
)
from src.ai_tools.colleague_mail.colleague_send.protocols.i_send_result import (
    ISendResult,
)

EDITORS = "editors"
DELIVERED = "in_recipient_inbox"
OUTCOME_LEGEND = (
    "in_recipient_inbox — письмо лежит в ящике ассистента адресата (прочитано ли — "
    "неизвестно); no_recipient — ящика с таким ключом нет, письмо не ушло; "
    "broker_unavailable — брокер недоступен или отказал, письмо не ушло."
)


class ColleagueSendInput(BaseModel):
    to: str = Field(
        pattern=r"^(editors|[a-z0-9][a-z0-9-]*)$",
        description=(
            "Ключ ассистента коллеги из инструмента colleagues или editors — всем "
            "редакторам общих агентов из справочника."
        ),
    )
    type: ColleagueMessageKind = Field(
        description=(
            "remark — замечание к общему агенту, question — вопрос, answer — ответ на "
            "письмо коллеги."
        ),
    )
    text: str = Field(
        min_length=1,
        description="Текст письма ровно в том виде, в каком его одобрил владелец.",
    )
    in_reply_to: str | None = Field(
        default=None,
        description="message_id письма коллеги, на которое это ответ (из colleague_messages).",
    )
    about_agent: str | None = Field(
        default=None,
        description="Имя общего агента, к которому относится замечание.",
    )


class ColleagueSendTool(BaseTool):
    name: ClassVar[str] = "colleague_send"
    description: ClassVar[str] = (
        "Отправить письмо ассистенту коллеги (или всем редакторам — to=editors) через "
        "почту ассистентов. Звать только после того, как владелец увидел точный текст и "
        "адресата и явно ответил «да». Итог — по каждому адресату."
    )
    Input: ClassVar[type[BaseModel]] = ColleagueSendInput

    def __init__(
        self, gateway: IColleagueMailGateway, directory: IColleagueDirectory | None
    ) -> None:
        self._gateway = gateway
        self._directory = directory

    def execute(self, input: ColleagueSendInput, context: ToolContext) -> str:
        if input.to != EDITORS:
            return self._report([self._send(input.to, input)])
        if self._directory is None:
            return (
                "Справочник коллег не подключён — редакторов не узнать, письмо не "
                "отправлено. Нужен ключ конкретного адресата."
            )
        editors = [
            colleague.key
            for colleague in self._directory.colleagues()
            if colleague.editor
        ]
        if not editors:
            return "В справочнике коллег нет редакторов — письмо не отправлено."
        return self._report([self._send(editor, input) for editor in editors])

    def _send(
        self, recipient: str, input: ColleagueSendInput
    ) -> tuple[str, ISendResult]:
        return recipient, self._gateway.send(
            recipient=recipient,
            message_type=input.type,
            text=input.text,
            in_reply_to=input.in_reply_to,
            about_agent=input.about_agent,
        )

    def _report(self, results: Sequence[tuple[str, ISendResult]]) -> str:
        lines = "\n".join(
            self._line(recipient, result) for recipient, result in results
        )
        return f"{lines}\n{OUTCOME_LEGEND}"

    def _line(self, recipient: str, result: ISendResult) -> str:
        if result.outcome == DELIVERED:
            return f"{recipient}: {result.outcome} (message_id {result.message_id})"
        return f"{recipient}: {result.outcome}"
