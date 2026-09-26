import json
from urllib.parse import parse_qs

import httpx

from src.gmail.repos.oauth_access_token_provider import (
    GOOGLE_OAUTH_URL,
    OAuthAccessTokenProvider,
)


def fake(name: str) -> str:
    return f"fake-{name}"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def token_endpoint(requests: list[httpx.Request]) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            content=json.dumps(
                {
                    "access_token": f"access-{len(requests)}",
                    "expires_in": 3599,
                    "token_type": "Bearer",
                }
            ),
        )

    return httpx.MockTransport(handle)


def make_provider(
    requests: list[httpx.Request], clock: FakeClock
) -> OAuthAccessTokenProvider:
    return OAuthAccessTokenProvider(
        http=httpx.Client(transport=token_endpoint(requests)),
        client_id=fake("client-id"),
        client_secret=fake("client-secret"),
        refresh_token=fake("refresh-token"),
        clock=clock,
    )


def test_exchanges_refresh_token_for_access_token() -> None:
    requests: list[httpx.Request] = []
    provider = make_provider(requests, FakeClock())

    assert provider.access_token() == "access-1"

    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == GOOGLE_OAUTH_URL
    assert parse_qs(request.content.decode()) == {
        "grant_type": ["refresh_token"],
        "client_id": [fake("client-id")],
        "client_secret": [fake("client-secret")],
        "refresh_token": [fake("refresh-token")],
    }


def test_reuses_token_until_expiry_then_refreshes() -> None:
    requests: list[httpx.Request] = []
    clock = FakeClock()
    provider = make_provider(requests, clock)

    provider.access_token()
    clock.now += 3000
    assert provider.access_token() == "access-1"
    clock.now += 600
    assert provider.access_token() == "access-2"
    assert len(requests) == 2
