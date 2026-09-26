from ai_framework import BaseTool

from src.ai_tools.file_read import FileReadTool, UntrustedFileFrame
from src.ai_tools.file_send import FileSendTool
from src.ai_tools.file_send.protocols.i_document_sender import IDocumentSender
from src.ai_tools.file_take import FileTakeTool
from src.ai_tools.file_view import FileViewTool
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.files.imaging import FileImageRenderer, ImageFitter, PdfRasterizer
from src.files.overflow.overflow_folder import OverflowFolder
from src.files.readers.file_text_reader import FileTextReader
from src.files.sources.chat_attachments.chat_attachments import ChatAttachments
from src.files.sources.chat_source.chat_file_source import ChatFileSource
from src.files.sources.dropbox_source.dropbox_file_source import DropboxFileSource
from src.files.sources.mail_source.mail_file_source import MailFileSource
from src.files.work_folder.work_folder import WorkFolder
from src.gmail.repos.gmail_client import GmailClient

FILE_TAKE_LIMIT_BYTES = 50 * 1024 * 1024
TELEGRAM_BOT_UPLOAD_LIMIT_BYTES = 50 * 1024 * 1024
PDF_RENDER_DPI = 150


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
