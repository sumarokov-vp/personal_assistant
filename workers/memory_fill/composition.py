from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from ai_framework import AIApplication, BaseTool, Provider

from src.ai_tools import (
    MemoryShowTool,
    MemoryUpsertCommitmentTool,
    MemoryUpsertDeadlineTool,
    MemoryUpsertTripTool,
)
from src.ai_tools.dropbox_read import DropboxReadTool
from src.ai_tools.dropbox_search import DropboxSearchTool
from src.ai_tools.dropbox_tree import DropboxTreeTool
from src.ai_tools.read_mail.tool import ReadMailTool
from src.ai_tools.search_mail.tool import SearchMailTool
from src.chat.actions.system_prompt_builder import SystemPromptBuilder
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.reader.dropbox_reader import DropboxReader
from src.dropbox.services.search.dropbox_search import DropboxSearch
from src.dropbox.services.tree.dropbox_tree import DropboxTree
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
from src.memory.repos import (
    CommitmentRepository,
    DeadlineRepository,
    IWikiStorage,
    WhereaboutsRepository,
    WikiPageStorage,
)
from src.memory.repos.formats.commitment_page_format import CommitmentPageFormat
from src.memory.repos.formats.deadline_page_format import DeadlinePageFormat
from src.memory.repos.formats.whereabouts_page_format import WhereaboutsPageFormat
from src.wiki import WikiFactory, WikiPageNotFoundError, WikiSettings
from workers.memory_fill.gmail_credentials import GmailCredentials
from workers.memory_fill.memory_fill_env import MemoryFillEnv
from workers.memory_fill.memory_fill_report import MemoryFillReport
from workers.memory_fill.memory_fill_run import MemoryFillRun
from workers.memory_fill.protocols.i_fill_conversation import IFillConversation
from workers.memory_fill.protocols.i_mail_source import IMailSource
from workers.memory_fill.protocols.i_watched_page import IWatchedPage
from workers.memory_fill.watched_page import WatchedPage

MEMORY_FILL_PROMPT_PATH = (
    Path(__file__).parent.parent.parent / "data" / "memory_fill_prompt.txt"
)
HTTP_TIMEOUT_SECONDS = 30.0
SUBSCRIPTION_HAS_NO_API_KEY = ""
DROPBOX_SOURCE = "Dropbox (dropbox_tree, dropbox_search, dropbox_read)"
MAIL_SOURCE = "почта Gmail (search_mail, read_mail)"


def build_wiki_storage(settings: WikiSettings) -> IWikiStorage:
    factory = WikiFactory(settings)
    return WikiPageStorage(
        reader=factory.create_reader(),
        writer=factory.create_writer(),
        page_not_found_error=WikiPageNotFoundError,
    )


def build_mail_client(http: httpx.Client, credentials: GmailCredentials) -> GmailClient:
    return GmailClient(
        http=http,
        token_provider=OAuthAccessTokenProvider(
            http=http,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            refresh_token=credentials.refresh_token,
        ),
        parser=GmailMessageParser(HtmlToTextConverter()),
        composer=ReplyMimeComposer(),
    )


def build_memory_fill_tools(
    dropbox_root: Path | None,
    mail: IMailSource | None,
    storage: IWikiStorage,
    timezone: ZoneInfo,
) -> list[BaseTool]:
    tools: list[BaseTool] = []
    if dropbox_root is not None:
        if not dropbox_root.is_dir():
            raise ValueError(f"DROPBOX_ROOT={dropbox_root} is not a directory")
        boundary = DropboxBoundary(root=dropbox_root, policy=DropboxAccessPolicy())
        tools.extend(
            [
                DropboxTreeTool(tree_builder=DropboxTree(boundary=boundary)),
                DropboxSearchTool(finder=DropboxSearch(boundary=boundary)),
                DropboxReadTool(reader=DropboxReader(boundary=boundary)),
            ]
        )
    if mail is not None:
        frame = UntrustedMailFrame()
        tools.extend(
            [
                SearchMailTool(searcher=mail, frame=frame),
                ReadMailTool(reader=mail, frame=frame),
            ]
        )
    deadlines = DeadlineRepository(storage)
    whereabouts = WhereaboutsRepository(storage)
    commitments = CommitmentRepository(storage)
    tools.extend(
        [
            MemoryShowTool(
                deadlines=deadlines, whereabouts=whereabouts, commitments=commitments
            ),
            MemoryUpsertDeadlineTool(deadlines=deadlines, timezone=timezone),
            MemoryUpsertTripTool(whereabouts=whereabouts),
            MemoryUpsertCommitmentTool(commitments=commitments),
        ]
    )
    return tools


def build_watched_pages(storage: IWikiStorage) -> list[IWatchedPage]:
    deadlines = DeadlinePageFormat()
    whereabouts = WhereaboutsPageFormat()
    commitments = CommitmentPageFormat()
    return [
        WatchedPage(deadlines.title, DeadlineRepository(storage), deadlines.key),
        WatchedPage(whereabouts.title, WhereaboutsRepository(storage), whereabouts.key),
        WatchedPage(commitments.title, CommitmentRepository(storage), commitments.key),
    ]


def build_kickoff(has_dropbox: bool, has_mail: bool) -> str:
    sources = [
        source
        for source, available in (
            (DROPBOX_SOURCE, has_dropbox),
            (MAIL_SOURCE, has_mail),
        )
        if available
    ]
    if not sources:
        raise ValueError("Memory fill needs DROPBOX_ROOT or GMAIL_* credentials")
    return (
        "Проведи наполнение памяти по инструкции. Доступные источники: "
        + "; ".join(sources)
        + ". Когда закончишь, ответь короткой сводкой: что записано и чего не нашлось."
    )


def build_memory_fill_run(
    conversation: IFillConversation,
    storage: IWikiStorage,
    kickoff: str,
    thread_id: str,
) -> MemoryFillRun:
    return MemoryFillRun(
        conversation=conversation,
        pages=build_watched_pages(storage),
        thread_id=thread_id,
        kickoff=kickoff,
    )


def build_fill_system_prompt(template: str, timezone: ZoneInfo) -> str:
    return SystemPromptBuilder(template=template, timezone=timezone).build()


def new_thread_id() -> str:
    return f"memory_fill:{datetime.now(tz=UTC):%Y%m%dT%H%M%S}"


def run_memory_fill(env: MemoryFillEnv, prompt_template: str) -> MemoryFillReport:
    storage = build_wiki_storage(env.wiki)
    kickoff = build_kickoff(
        has_dropbox=env.dropbox_root is not None, has_mail=env.gmail is not None
    )
    with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as http:
        mail = build_mail_client(http, env.gmail) if env.gmail else None
        ai = AIApplication(
            api_key=SUBSCRIPTION_HAS_NO_API_KEY,
            provider=Provider.CLAUDE_SDK,
            model=env.ai_model,
            system_prompt=build_fill_system_prompt(prompt_template, env.owner_timezone),
            database_url=env.ai_db_url,
            tools=build_memory_fill_tools(
                env.dropbox_root, mail, storage, env.owner_timezone
            ),
            max_tool_rounds=env.max_tool_rounds,
        )
        run = build_memory_fill_run(ai, storage, kickoff, new_thread_id())
        with ai:
            return run.execute()
