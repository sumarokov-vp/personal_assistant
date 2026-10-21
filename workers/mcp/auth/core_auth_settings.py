from pathlib import Path

from pydantic import BaseModel


class CoreAuthSettings(BaseModel):
    oidc_config_url: str
    oidc_client_id: str
    oidc_client_secret: str
    public_url: str
    jwt_signing_key: str
    storage_dir: Path
    allowed_emails: frozenset[str]
    extra_authorize_params: dict[str, str] = {}
