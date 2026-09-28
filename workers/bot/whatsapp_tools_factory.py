from pathlib import Path
from zoneinfo import ZoneInfo

from ai_framework import BaseTool

from src.ai_tools.list_whatsapp_chats import ListWhatsAppChatsTool
from src.ai_tools.read_whatsapp import ReadWhatsAppTool
from src.ai_tools.search_whatsapp import SearchWhatsAppTool
from src.ai_tools.whatsapp_common import UntrustedWhatsAppFrame, WhatsAppFreshnessNote
from src.whatsapp.macos_desktop.repos.whatsapp_cdn_client import WhatsAppCdnClient
from src.whatsapp.macos_desktop.services.conversation_source.whatsapp_conversation_source import (
    WhatsAppConversationSource,
)
from workers.bot.protocols.i_whatsapp_source import IWhatsAppSource

WHATSAPP_MACOS_SNAPSHOT_VARIABLE = "WHATSAPP_MACOS_SNAPSHOT_DIR"
MEDIA_CACHE_FOLDER = "whatsapp-media"


def build_whatsapp_source(
    macos_snapshot_dir: str | None, timezone: ZoneInfo, work_dir: Path
) -> IWhatsAppSource | None:
    if macos_snapshot_dir:
        return WhatsAppConversationSource(
            snapshot_dir=Path(macos_snapshot_dir),
            timezone=timezone,
            media_cache_dir=work_dir / MEDIA_CACHE_FOLDER,
            cdn_client=WhatsAppCdnClient(),
        )
    return None


def build_whatsapp_tools(source: IWhatsAppSource, timezone: ZoneInfo) -> list[BaseTool]:
    frame = UntrustedWhatsAppFrame()
    freshness = WhatsAppFreshnessNote(source, timezone)
    return [
        SearchWhatsAppTool(
            searcher=source, freshness=freshness, frame=frame, timezone=timezone
        ),
        ReadWhatsAppTool(
            reader=source, freshness=freshness, frame=frame, timezone=timezone
        ),
        ListWhatsAppChatsTool(directory=source, freshness=freshness, frame=frame),
    ]
