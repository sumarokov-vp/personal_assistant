import tempfile
from dataclasses import dataclass
from os import getenv
from pathlib import Path
from zoneinfo import ZoneInfo

from src.wiki import WikiSettings
from workers.memory_fill.gmail_credentials import GmailCredentials

DEFAULT_MAX_TOOL_ROUNDS = 120
DEFAULT_WIKI_DIR = Path(tempfile.gettempdir()) / "memory_fill_wiki"
GMAIL_VARIABLES = ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN")


@dataclass(frozen=True)
class MemoryFillEnv:
    ai_model: str
    ai_db_url: str
    owner_timezone: ZoneInfo
    wiki: WikiSettings
    dropbox_root: Path | None
    gmail: GmailCredentials | None
    max_tool_rounds: int


def require_env(name: str) -> str:
    value = getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def read_memory_fill_env() -> MemoryFillEnv:
    dropbox_root = getenv("DROPBOX_ROOT")
    ssh_key_path = getenv("WIKI_SSH_KEY_PATH")
    return MemoryFillEnv(
        ai_model=require_env("AI_MODEL"),
        ai_db_url=require_env("AI_DB_URL"),
        owner_timezone=ZoneInfo(getenv("OWNER_TIMEZONE", "Asia/Almaty")),
        wiki=WikiSettings(
            wiki_dir=Path(getenv("MEMORY_FILL_WIKI_DIR", str(DEFAULT_WIKI_DIR))),
            remote_url=require_env("WIKI_REMOTE_URL"),
            ssh_key_path=Path(ssh_key_path) if ssh_key_path else None,
        ),
        dropbox_root=Path(dropbox_root) if dropbox_root else None,
        gmail=_read_gmail_credentials(),
        max_tool_rounds=int(
            getenv("MEMORY_FILL_MAX_TOOL_ROUNDS", str(DEFAULT_MAX_TOOL_ROUNDS))
        ),
    )


def _read_gmail_credentials() -> GmailCredentials | None:
    values = [getenv(name) for name in GMAIL_VARIABLES]
    if not any(values):
        return None
    client_id, client_secret, refresh_token = (
        require_env(name) for name in GMAIL_VARIABLES
    )
    return GmailCredentials(
        client_id=client_id, client_secret=client_secret, refresh_token=refresh_token
    )
