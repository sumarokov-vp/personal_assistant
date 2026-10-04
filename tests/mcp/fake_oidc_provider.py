import secrets
from urllib.parse import urlencode

from fastmcp.server.auth.providers.jwt import RSAKeyPair
from joserfc.jwk import RSAKey
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route

SIGNING_KEY_ID = "fake-key-1"


class FakeOidcProvider:
    def __init__(self, issuer: str, client_id: str, email: str) -> None:
        self.issuer = issuer
        self.client_id = client_id
        self.email = email
        self.email_verified = True
        self.authorize_requests: list[dict[str, str]] = []
        self._keys = RSAKeyPair.generate()
        self._codes: dict[str, str] = {}

    @property
    def config_url(self) -> str:
        return f"{self.issuer}/.well-known/openid-configuration"

    @property
    def authorization_endpoint(self) -> str:
        return f"{self.issuer}/authorize"

    def app(self) -> Starlette:
        return Starlette(
            routes=[
                Route("/.well-known/openid-configuration", self._discovery),
                Route("/authorize", self._authorize),
                Route("/token", self._token, methods=["POST"]),
                Route("/jwks", self._jwks),
            ]
        )

    async def _discovery(self, request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "issuer": self.issuer,
                "authorization_endpoint": self.authorization_endpoint,
                "token_endpoint": f"{self.issuer}/token",
                "jwks_uri": f"{self.issuer}/jwks",
                "response_types_supported": ["code"],
                "subject_types_supported": ["public"],
                "id_token_signing_alg_values_supported": ["RS256"],
            }
        )

    async def _authorize(self, request: Request) -> RedirectResponse:
        params = dict(request.query_params)
        self.authorize_requests.append(params)
        code = secrets.token_urlsafe(16)
        self._codes[code] = self.email
        query = urlencode({"code": code, "state": params["state"]})
        return RedirectResponse(f"{params['redirect_uri']}?{query}", status_code=302)

    async def _token(self, request: Request) -> JSONResponse:
        form = await request.form()
        email = self._codes.pop(str(form["code"]))
        id_token = self._keys.create_token(
            subject=f"sub-{email}",
            issuer=self.issuer,
            audience=self.client_id,
            additional_claims={"email": email, "email_verified": self.email_verified},
            kid=SIGNING_KEY_ID,
        )
        return JSONResponse(
            {
                "access_token": secrets.token_urlsafe(24),
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "openid email",
                "id_token": id_token,
            }
        )

    async def _jwks(self, request: Request) -> JSONResponse:
        key = RSAKey.import_key(self._keys.public_key)
        return JSONResponse(
            {"keys": [key.as_dict(kid=SIGNING_KEY_ID, use="sig", alg="RS256")]}
        )
