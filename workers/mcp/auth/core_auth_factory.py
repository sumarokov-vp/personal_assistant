from cryptography.fernet import Fernet
from fastmcp.server.auth.jwt_issuer import derive_jwt_key
from fastmcp.server.auth.oidc_proxy import OIDCConfiguration
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.auth.redirect_validation import DEFAULT_LOCALHOST_PATTERNS
from key_value.aio.protocols import AsyncKeyValue
from key_value.aio.stores.filetree import (
    FileTreeStore,
    FileTreeV1CollectionSanitizationStrategy,
    FileTreeV1KeySanitizationStrategy,
)
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from pydantic import AnyHttpUrl

from workers.mcp.auth.allowlist_oidc_proxy import AllowlistOIDCProxy
from workers.mcp.auth.allowlist_token_verifier import AllowlistTokenVerifier
from workers.mcp.auth.core_auth_settings import CoreAuthSettings
from workers.mcp.auth.email_allowlist import EmailAllowlist
from workers.mcp.auth.protocols.i_denial_journal import IDenialJournal

SIGN_IN_SCOPES = ["openid", "email"]
CLIENT_REDIRECT_URI_PATTERNS = [
    "https://claude.ai/*",
    "https://claude.com/*",
    "https://chatgpt.com/*",
    *DEFAULT_LOCALHOST_PATTERNS,
]
STORAGE_KEY_SALT = "assistant-core-oauth-storage"
DISCOVERY_TIMEOUT_SECONDS = 10


def build_core_auth(
    settings: CoreAuthSettings, denials: IDenialJournal
) -> AllowlistOIDCProxy:
    return AllowlistOIDCProxy(
        config_url=settings.oidc_config_url,
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        base_url=settings.public_url,
        token_verifier=AllowlistTokenVerifier(
            identity=_id_token_verifier(settings),
            allowlist=EmailAllowlist(settings.allowed_emails),
            denials=denials,
        ),
        verify_id_token=True,
        valid_scopes=SIGN_IN_SCOPES,
        extra_authorize_params={
            **settings.extra_authorize_params,
            "scope": " ".join(SIGN_IN_SCOPES),
        },
        allowed_client_redirect_uris=CLIENT_REDIRECT_URI_PATTERNS,
        client_storage=_encrypted_storage(settings),
        jwt_signing_key=settings.jwt_signing_key,
    )


def _id_token_verifier(settings: CoreAuthSettings) -> JWTVerifier:
    discovery = OIDCConfiguration.get_oidc_configuration(
        AnyHttpUrl(settings.oidc_config_url),
        strict=None,
        timeout_seconds=DISCOVERY_TIMEOUT_SECONDS,
    )
    return JWTVerifier(
        jwks_uri=str(discovery.jwks_uri),
        issuer=str(discovery.issuer),
        audience=settings.oidc_client_id,
    )


def _encrypted_storage(settings: CoreAuthSettings) -> AsyncKeyValue:
    directory = settings.storage_dir
    directory.mkdir(parents=True, exist_ok=True)
    return FernetEncryptionWrapper(
        key_value=FileTreeStore(
            data_directory=directory,
            key_sanitization_strategy=FileTreeV1KeySanitizationStrategy(directory),
            collection_sanitization_strategy=FileTreeV1CollectionSanitizationStrategy(
                directory
            ),
        ),
        fernet=Fernet(
            key=derive_jwt_key(
                high_entropy_material=settings.jwt_signing_key, salt=STORAGE_KEY_SALT
            )
        ),
        raise_on_decryption_error=False,
    )
