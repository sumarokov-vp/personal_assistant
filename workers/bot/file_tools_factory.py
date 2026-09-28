from ai_framework import BaseTool

from src.ai_tools.file_read import FileReadTool, UntrustedFileFrame
from src.ai_tools.file_send import FileSendTool
from src.ai_tools.file_send.protocols.i_document_sender import IDocumentSender
from src.ai_tools.file_take import FileTakeTool, RegisteredFileSource
from src.ai_tools.file_take.protocols.i_file_source import IFileSource
from src.ai_tools.file_view import FileViewTool
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.files.imaging import FileImageRenderer, ImageFitter, PdfRasterizer
from src.files.overflow.overflow_folder import OverflowFolder
from src.files.readers.file_text_reader import FileTextReader
from src.files.sources.chat_attachments.chat_attachments import ChatAttachments
from src.files.sources.chat_source.chat_file_source import ChatFileSource
from src.files.sources.dropbox_source.dropbox_file_source import DropboxFileSource
from src.files.sources.dropbox_source.protocols.i_dropbox_file_opener import (
    IDropboxFileOpener,
)
from src.files.sources.mail_source.mail_file_source import MailFileSource
from src.files.sources.mail_source.protocols.i_mail_attachments import (
    IMailAttachments,
)
from src.files.sources.unavailable_source.unavailable_file_source import (
    UnavailableFileSource,
)
from src.files.work_folder.work_folder import WorkFolder
from src.gmail.repos.gmail_client import GmailClient

FILE_TAKE_LIMIT_BYTES = 50 * 1024 * 1024
TELEGRAM_BOT_UPLOAD_LIMIT_BYTES = 50 * 1024 * 1024
PDF_RENDER_DPI = 150

MAIL_HINT = "вложение письма: message_id и attachment_id из read_mail"
DROPBOX_HINT = "файл Dropbox: path относительно корня Dropbox"
CHAT_HINT = (
    "вложение, которое владелец прислал в чат за всю историю треда: "
    "attachment_filename — имя из метки «[вложение: …]» его сообщения или ключ S3, "
    "не указано — последнее"
)


def build_file_take_tool(
    work_folder: WorkFolder,
    chat_attachments: ChatAttachments,
    dropbox_boundary: IDropboxFileOpener | None,
    mail: IMailAttachments | None,
) -> FileTakeTool:
    mail_source: IFileSource = (
        MailFileSource(mail, FILE_TAKE_LIMIT_BYTES)
        if mail is not None
        else UnavailableFileSource("Почта не подключена — вложения писем не достать")
    )
    dropbox_source: IFileSource = (
        DropboxFileSource(dropbox_boundary, FILE_TAKE_LIMIT_BYTES)
        if dropbox_boundary is not None
        else UnavailableFileSource("Dropbox не подключён — файлы из него не достать")
    )
    return FileTakeTool(
        work_files=work_folder,
        sources=[
            RegisteredFileSource("mail", MAIL_HINT, mail_source),
            RegisteredFileSource("dropbox", DROPBOX_HINT, dropbox_source),
            RegisteredFileSource(
                "chat",
                CHAT_HINT,
                ChatFileSource(chat_attachments, FILE_TAKE_LIMIT_BYTES),
            ),
        ],
    )


def build_file_tools(
    work_folder: WorkFolder,
    text_reader: FileTextReader,
    chat_attachments: ChatAttachments,
    dropbox_boundary: DropboxBoundary | None,
    mail: GmailClient | None,
    max_image_bytes: int,
    document_sender: IDocumentSender,
    owner_chat_id: int,
) -> list[BaseTool]:
    return [
        build_file_take_tool(work_folder, chat_attachments, dropbox_boundary, mail),
        FileReadTool(
            work_files=work_folder, text_reader=text_reader, frame=UntrustedFileFrame()
        ),
        FileViewTool(
            work_files=work_folder,
            renderer=FileImageRenderer(
                fitter=ImageFitter(max_image_bytes),
                rasterizer=PdfRasterizer(PDF_RENDER_DPI),
            ),
        ),
        FileSendTool(
            work_files=work_folder,
            sender=document_sender,
            owner_chat_id=owner_chat_id,
            size_limit_bytes=TELEGRAM_BOT_UPLOAD_LIMIT_BYTES,
            overflow=(
                OverflowFolder(dropbox_boundary, work_folder)
                if dropbox_boundary is not None
                else None
            ),
        ),
    ]
