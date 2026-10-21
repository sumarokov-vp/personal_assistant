from fastmcp.server.auth import AccessToken, TokenVerifier

from workers.mcp.auth.email_allowlist import EMAIL_CLAIM, EmailAllowlist
from workers.mcp.auth.protocols.i_denial_journal import IDenialJournal


class AllowlistTokenVerifier(TokenVerifier):
    def __init__(
        self,
        identity: TokenVerifier,
        allowlist: EmailAllowlist,
        denials: IDenialJournal,
    ) -> None:
        super().__init__()
        self._identity = identity
        self._allowlist = allowlist
        self._denials = denials

    async def verify_token(self, token: str) -> AccessToken | None:
        verified = await self._identity.verify_token(token)
        if verified is None:
            return None
        if not self._allowlist.admits(verified.claims):
            email = verified.claims.get(EMAIL_CLAIM)
            self._denials.record_denied(email if isinstance(email, str) else None)
            return None
        return verified
