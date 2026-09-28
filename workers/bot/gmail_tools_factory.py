import httpx
from ai_framework import BaseTool

from src.ai_tools.draft_mail import DraftAttachments, DraftMailTool
from src.ai_tools.draft_reply.tool import DraftReplyTool
from src.ai_tools.read_mail.tool import ReadMailTool
from src.ai_tools.search_mail.tool import SearchMailTool
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.files.overflow.overflow_folder import OverflowFolder
from src.files.work_folder.work_folder import WorkFolder
from src.gmail.repos.gmail_client import GmailClient
from src.gmail.repos.oauth_access_token_provider import OAuthAccessTokenProvider
from src.gmail.services.conversation_source.gmail_conversation_source import (
    GmailConversationSource,
)
from src.gmail.services.gmail_message_parser.gmail_message_parser import (
    GmailMessageParser,
)
from src.gmail.services.gmail_message_parser.html_to_text_converter import (
    HtmlToTextConverter,
)
from src.gmail.services.reply_mime_composer.reply_mime_composer import (
    ReplyMimeComposer,
)
from src.gmail.services.untrusted_frame.untrusted_mail_frame import UntrustedMailFrame

GMAIL_VARIABLES = ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN")


def build_gmail_client(
    http: httpx.Client, client_id: str, client_secret: str, refresh_token: str
) -> GmailClient:
    return GmailClient(
        http=http,
        token_provider=OAuthAccessTokenProvider(
            http=http,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
        ),
        parser=GmailMessageParser(HtmlToTextConverter()),
        composer=ReplyMimeComposer(),
    )


def build_gmail_tools(
    mail: GmailClient,
    work_folder: WorkFolder,
    dropbox_boundary: DropboxBoundary | None,
) -> list[BaseTool]:
    frame = UntrustedMailFrame()
    conversations = GmailConversationSource(mail)
    attachments = DraftAttachments(
        work_files=work_folder,
        overflow=(
            OverflowFolder(dropbox_boundary, work_folder)
            if dropbox_boundary is not None
            else None
        ),
    )
    return [
        SearchMailTool(searcher=conversations, frame=frame),
        ReadMailTool(reader=conversations, frame=frame),
        DraftReplyTool(drafter=mail, frame=frame, attachments=attachments),
        DraftMailTool(drafter=mail, attachments=attachments),
    ]
