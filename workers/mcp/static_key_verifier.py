from hmac import compare_digest

from fastmcp.server.auth import AccessToken, TokenVerifier

STATIC_KEY_CLIENT_ID = "static-key"


class StaticKeyVerifier(TokenVerifier):
    def __init__(self, key: str) -> None:
        super().__init__()
        self._key = key.encode()

    async def verify_token(self, token: str) -> AccessToken | None:
        if not compare_digest(token.encode(), self._key):
            return None
        return AccessToken(token=token, client_id=STATIC_KEY_CLIENT_ID, scopes=[])
