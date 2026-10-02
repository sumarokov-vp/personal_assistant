from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel

DEFAULT_MCP_HOST = "127.0.0.1"
DEFAULT_MCP_PORT = 8790


class CoreSettings(BaseModel):
    todoist_token: str
    dropbox_root: Path
    static_key: str
    journal_file: Path
    allowed_projects: frozenset[str] = frozenset()
    host: str = DEFAULT_MCP_HOST
    port: int = DEFAULT_MCP_PORT
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "CoreSettings":
        return cls(
            todoist_token=_require(env, "TODOIST_TOKEN"),
            dropbox_root=Path(_require(env, "DROPBOX_ROOT")),
            static_key=_require(env, "MCP_STATIC_KEY"),
            journal_file=Path(_require(env, "MCP_JOURNAL_FILE")),
            allowed_projects=_comma_separated(env.get("MCP_ALLOWED_PROJECTS") or ""),
            host=env.get("MCP_HOST") or DEFAULT_MCP_HOST,
            port=int(env.get("MCP_PORT") or DEFAULT_MCP_PORT),
            log_level=env.get("LOG_LEVEL") or "INFO",
        )


def _require(env: Mapping[str, str], name: str) -> str:
    value = env.get(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def _comma_separated(value: str) -> frozenset[str]:
    return frozenset(item.strip() for item in value.split(",") if item.strip())
