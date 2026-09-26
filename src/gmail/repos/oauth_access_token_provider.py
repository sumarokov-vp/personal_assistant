import time
from collections.abc import Callable

import httpx

GOOGLE_OAUTH_URL = "https://oauth2.googleapis.com/token"
EXPIRY_MARGIN_SECONDS = 60.0


class OAuthAccessTokenProvider:
    def __init__(
        self,
        http: httpx.Client,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        oauth_url: str = GOOGLE_OAUTH_URL,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._http = http
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._oauth_url = oauth_url
        self._clock = clock
        self._access_token: str | None = None
        self._expires_at = 0.0

    def access_token(self) -> str:
        if self._access_token is None or self._clock() >= self._expires_at:
            self._refresh()
        return str(self._access_token)

    def _refresh(self) -> None:
        response = self._http.post(
            self._oauth_url,
            data={
                "grant_type": "refresh_token",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
            },
        )
        response.raise_for_status()
        payload = response.json()
        self._access_token = payload["access_token"]
        self._expires_at = (
            self._clock() + float(payload["expires_in"]) - EXPIRY_MARGIN_SECONDS
        )
