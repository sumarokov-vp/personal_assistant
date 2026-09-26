from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, Field

from src.ai_tools.draft_reply.protocols.i_reply_drafter import IReplyDrafter
from src.ai_tools.draft_reply.protocols.i_untrusted_frame import IUntrustedFrame


class DraftReplyInput(BaseModel):
    message_id: str = Field(
        pattern=r"^[A-Za-z0-9]+$",
        description="id письма, на которое готовится ответ (из search_mail или read_mail)",
    )
    body: str = Field(min_length=1, description="текст ответа")


class DraftReplyTool(BaseTool):
    name = "draft_reply"
    description = (
        "Готовит черновик ответа на письмо Gmail в том же треде. Адресат и тема берутся "
        "из исходного письма. Письмо не отправляется: владелец проверит черновик и отправит сам."
    )
    Input = DraftReplyInput

    def __init__(self, drafter: IReplyDrafter, frame: IUntrustedFrame) -> None:
        self._drafter = drafter
        self._frame = frame

    def execute(self, input: DraftReplyInput, context: ToolContext) -> str:
        draft = self._drafter.create_reply_draft(input.message_id, input.body)
        addressing = f"кому: {draft.recipient}\nтема: {draft.subject}"
        return (
            f"Черновик {draft.id} создан в треде {draft.thread_id}, не отправлен.\n"
            f"Ссылка: {draft.url}\n"
            f"{self._frame.wrap(addressing)}"
        )
