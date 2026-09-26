from ai_framework import BaseTool

from src.ai_tools.file_read import FileReadTool, UntrustedFileFrame
from src.ai_tools.file_take import FileTakeTool
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.files.readers.file_text_reader import FileTextReader
from src.files.sources.chat_attachments.chat_attachments import ChatAttachments
from src.files.sources.chat_source.chat_file_source import ChatFileSource
from src.files.sources.dropbox_source.dropbox_file_source import DropboxFileSource
from src.files.sources.mail_source.mail_file_source import MailFileSource
from src.files.work_folder.work_folder import WorkFolder
from src.gmail.repos.gmail_client import GmailClient

FILE_TAKE_LIMIT_BYTES = 50 * 1024 * 1024


def build_file_tools(
    work_folder: WorkFolder,
    text_reader: FileTextReader,
    chat_attachments: ChatAttachments,
    dropbox_boundary: DropboxBoundary | None,
    mail: GmailClient | None,
) -> list[BaseTool]:
    return [
        FileTakeTool(
            work_files=work_folder,
            chat=ChatFileSource(chat_attachments, FILE_TAKE_LIMIT_BYTES),
            dropbox=(
                DropboxFileSource(dropbox_boundary, FILE_TAKE_LIMIT_BYTES)
                if dropbox_boundary is not None
                else None
            ),
            mail=(
                MailFileSource(mail, FILE_TAKE_LIMIT_BYTES)
                if mail is not None
                else None
            ),
        ),
        FileReadTool(
            work_files=work_folder, text_reader=text_reader, frame=UntrustedFileFrame()
        ),
    ]
