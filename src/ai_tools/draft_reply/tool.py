import json

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, Field

from src.ai_tools.draft_reply.protocols.i_reply_attachments import IReplyAttachments
from src.ai_tools.draft_reply.protocols.i_reply_drafter import IReplyDrafter
from src.ai_tools.draft_reply.protocols.i_untrusted_frame import IUntrustedFrame
from src.files.work_folder.work_file_not_found_error import WorkFileNotFoundError


class DraftReplyInput(BaseModel):
    message_id: str = Field(
        pattern=r"^[A-Za-z0-9]+$",
        description="id письма, на которое готовится ответ (из search_mail или read_mail)",
    )
    body: str = Field(min_length=1, description="текст ответа")
    file_ids: list[str] = Field(
        default_factory=list,
        description="file_id вложений из file_take; не нужны вложения — пусто",
    )


class DraftReplyTool(BaseTool):
    name = "draft_reply"
    description = (
        "Готовит черновик ответа на письмо Gmail в том же треде. Адресат и тема берутся "
        "из исходного письма. Вложения — file_id из file_take; письмо Gmail не больше "
        "25 МБ: файл, который не влезает, не прикладывается — бот кладёт его в папку "
        "Personal Assistant в Dropbox и называет путь. Письмо не отправляется: владелец "
        "проверит черновик и отправит сам."
    )
    Input = DraftReplyInput

    def __init__(
        self,
        drafter: IReplyDrafter,
        frame: IUntrustedFrame,
        attachments: IReplyAttachments,
    ) -> None:
        self._drafter = drafter
        self._frame = frame
        self._attachments = attachments

    def execute(self, input: DraftReplyInput, context: ToolContext) -> str:
        try:
            files = self._attachments.collect(input.file_ids)
        except WorkFileNotFoundError as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        draft = self._drafter.create_reply_draft(input.message_id, input.body, files)
        addressing = f"кому: {draft.recipient}\nтема: {draft.subject}"
        lines = [
            f"Черновик {draft.id} создан в треде {draft.thread_id}, не отправлен.",
            f"Ссылка: {draft.url}",
            *self._attachments.settle(files, draft.attached, draft.left_out),
            self._frame.wrap(addressing),
        ]
        return "\n".join(lines)
