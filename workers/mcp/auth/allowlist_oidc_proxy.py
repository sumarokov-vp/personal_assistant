from typing import Any

from fastmcp.server.auth.oidc_proxy import OIDCProxy
from mcp.server.auth.provider import TokenError

from workers.mcp.auth.email_allowlist import EMAIL_CLAIM

ACCOUNT_NOT_ALLOWED = "Account is not allowed to use this server"


class AllowlistOIDCProxy(OIDCProxy):
    async def _extract_upstream_claims(
        self, idp_tokens: dict[str, Any]
    ) -> dict[str, Any] | None:
        id_token = idp_tokens.get("id_token")
        admitted = (
            await self._token_validator.verify_token(id_token)
            if isinstance(id_token, str)
            else None
        )
        if admitted is None:
            raise TokenError("invalid_grant", ACCOUNT_NOT_ALLOWED)
        return {EMAIL_CLAIM: admitted.claims.get(EMAIL_CLAIM)}
