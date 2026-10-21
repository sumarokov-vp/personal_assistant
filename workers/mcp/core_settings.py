from collections.abc import Mapping
from pathlib import Path
from urllib.parse import parse_qsl

from pydantic import BaseModel

from workers.mcp.auth.core_auth_settings import CoreAuthSettings

DEFAULT_MCP_HOST = "127.0.0.1"
DEFAULT_MCP_PORT = 8790


class CoreSettings(BaseModel):
    todoist_token: str
    dropbox_root: Path
    journal_file: Path
    auth: CoreAuthSettings
    allowed_projects: frozenset[str] = frozenset()
    host: str = DEFAULT_MCP_HOST
    port: int = DEFAULT_MCP_PORT
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "CoreSettings":
        return cls(
            todoist_token=_require(env, "TODOIST_TOKEN"),
            dropbox_root=Path(_require(env, "DROPBOX_ROOT")),
            journal_file=Path(_require(env, "MCP_JOURNAL_FILE")),
            auth=_auth_from_env(env),
            allowed_projects=_comma_separated(env.get("MCP_ALLOWED_PROJECTS") or ""),
            host=env.get("MCP_HOST") or DEFAULT_MCP_HOST,
            port=int(env.get("MCP_PORT") or DEFAULT_MCP_PORT),
            log_level=env.get("LOG_LEVEL") or "INFO",
        )


def _auth_from_env(env: Mapping[str, str]) -> CoreAuthSettings:
    allowed_emails = _comma_separated(_require(env, "MCP_ALLOWED_EMAILS"))
    if not allowed_emails:
        raise ValueError("MCP_ALLOWED_EMAILS must list at least one address")
    return CoreAuthSettings(
        oidc_config_url=_require(env, "MCP_OIDC_CONFIG_URL"),
        oidc_client_id=_require(env, "MCP_OIDC_CLIENT_ID"),
        oidc_client_secret=_require(env, "MCP_OIDC_CLIENT_SECRET"),
        public_url=_require(env, "MCP_PUBLIC_URL"),
        jwt_signing_key=_require(env, "MCP_JWT_SIGNING_KEY"),
        storage_dir=Path(_require(env, "MCP_OAUTH_STORAGE_DIR")),
        allowed_emails=allowed_emails,
        extra_authorize_params=dict(
            parse_qsl(env.get("MCP_OIDC_EXTRA_AUTHORIZE_PARAMS") or "")
        ),
    )


def _require(env: Mapping[str, str], name: str) -> str:
    value = env.get(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def _comma_separated(value: str) -> frozenset[str]:
    return frozenset(item.strip() for item in value.split(",") if item.strip())
