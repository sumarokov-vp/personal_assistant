import httpx
from ai_framework import BaseTool

from src.ai_tools.draft_reply.tool import DraftReplyTool
from src.ai_tools.read_mail.tool import ReadMailTool
from src.ai_tools.search_mail.tool import SearchMailTool
from src.gmail.repos.gmail_client import GmailClient
from src.gmail.repos.oauth_access_token_provider import OAuthAccessTokenProvider
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


def build_gmail_tools(mail: GmailClient) -> list[BaseTool]:
    frame = UntrustedMailFrame()
    return [
        SearchMailTool(searcher=mail, frame=frame),
        ReadMailTool(reader=mail, frame=frame),
        DraftReplyTool(drafter=mail, frame=frame),
    ]
