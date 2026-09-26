import json
from typing import ClassVar

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, Field

from src.ai_tools.draft_mail.protocols.i_draft_attachments import IDraftAttachments
from src.ai_tools.draft_mail.protocols.i_mail_drafter import IMailDrafter
from src.files.work_folder.work_file_not_found_error import WorkFileNotFoundError

SINGLE_LINE = r"^[^\r\n]+$"


class DraftMailInput(BaseModel):
    to: str = Field(
        min_length=3,
        pattern=SINGLE_LINE,
        description="адресат: e-mail или «Имя <e-mail>», несколько — через запятую",
    )
    subject: str = Field(min_length=1, pattern=SINGLE_LINE, description="тема письма")
    body: str = Field(min_length=1, description="текст письма")
    file_ids: list[str] = Field(
        default_factory=list,
        description="file_id вложений из file_take; не нужны вложения — пусто",
    )


class DraftMailTool(BaseTool):
    name: ClassVar[str] = "draft_mail"
    description: ClassVar[str] = (
        "Готовит черновик нового письма Gmail с адресатом, темой и текстом; вложения — "
        "file_id из file_take. Письмо не отправляется: владелец проверит черновик и "
        "отправит сам. Письмо Gmail не больше 25 МБ: файл, который не влезает, не "
        "прикладывается — бот кладёт его в папку Personal Assistant в Dropbox и называет "
        "путь. Ответ на существующее письмо — draft_reply, а не draft_mail."
    )

    Input: ClassVar[type[BaseModel]] = DraftMailInput

    def __init__(self, drafter: IMailDrafter, attachments: IDraftAttachments) -> None:
        self._drafter = drafter
        self._attachments = attachments

    def execute(self, input: DraftMailInput, context: ToolContext) -> str:  # noqa: A002
        try:
            files = self._attachments.collect(input.file_ids)
        except WorkFileNotFoundError as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        draft = self._drafter.create_draft(
            input.to.strip(), input.subject.strip(), input.body, files
        )
        lines = [
            f"Черновик {draft.id} создан, не отправлен.",
            f"Ссылка: {draft.url}",
            f"Кому: {draft.recipient}",
            f"Тема: {draft.subject}",
            *self._attachments.settle(files, draft.attached, draft.left_out),
        ]
        return "\n".join(lines)
