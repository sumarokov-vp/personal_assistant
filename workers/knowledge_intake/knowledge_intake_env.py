import tempfile
from dataclasses import dataclass
from os import getenv
from pathlib import Path
from zoneinfo import ZoneInfo

from src.knowledge_intake import ImapSettings, ToolkitSettings
from src.knowledge_intake.models.imap_settings import IMAPS_PORT

DEFAULT_TOOLKIT_REMOTE_URL = "git@github.com:mineradiosystems/claude-toolkit.git"
DEFAULT_TOOLKIT_DIR = (
    Path(tempfile.gettempdir()) / "knowledge_intake" / "claude-toolkit"
)
DEFAULT_PLUGINS = "mrs-finance"


@dataclass(frozen=True)
class KnowledgeIntakeEnv:
    ai_model: str
    ai_db_url: str
    owner_timezone: ZoneInfo
    imap: ImapSettings
    toolkit: ToolkitSettings
    allowlist_path: Path


def require_env(name: str) -> str:
    value = getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def read_knowledge_intake_env() -> KnowledgeIntakeEnv:
    ssh_key_path = getenv("KNOWLEDGE_TOOLKIT_SSH_KEY_PATH")
    allowlist_path = Path(require_env("KNOWLEDGE_ALLOWLIST_FILE"))
    if not allowlist_path.is_file():
        raise ValueError(f"KNOWLEDGE_ALLOWLIST_FILE={allowlist_path} is not a file")
    return KnowledgeIntakeEnv(
        ai_model=require_env("AI_MODEL"),
        ai_db_url=require_env("AI_DB_URL"),
        owner_timezone=ZoneInfo(getenv("OWNER_TIMEZONE", "Asia/Almaty")),
        imap=ImapSettings(
            host=require_env("KNOWLEDGE_IMAP_HOST"),
            user=require_env("KNOWLEDGE_IMAP_USER"),
            password=require_env("KNOWLEDGE_IMAP_PASSWORD"),
            port=int(getenv("KNOWLEDGE_IMAP_PORT", str(IMAPS_PORT))),
        ),
        toolkit=ToolkitSettings(
            clone_dir=Path(getenv("KNOWLEDGE_TOOLKIT_DIR", str(DEFAULT_TOOLKIT_DIR))),
            remote_url=getenv(
                "KNOWLEDGE_TOOLKIT_REMOTE_URL", DEFAULT_TOOLKIT_REMOTE_URL
            ),
            plugins=_plugins(getenv("KNOWLEDGE_PLUGINS", DEFAULT_PLUGINS)),
            ssh_key_path=Path(ssh_key_path) if ssh_key_path else None,
        ),
        allowlist_path=allowlist_path,
    )


def _plugins(value: str) -> tuple[str, ...]:
    plugins = tuple(name.strip() for name in value.split(",") if name.strip())
    if not plugins:
        raise ValueError("KNOWLEDGE_PLUGINS must name at least one plugin")
    return plugins
