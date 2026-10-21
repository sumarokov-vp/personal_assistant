import hashlib
import json
import re
import secrets
from base64 import urlsafe_b64encode
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import anyio
import httpx
import httpx2
import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp_types import CallToolResult

from tests.mcp.fake_oidc_provider import FakeOidcProvider
from tests.mcp.fake_todoist_read_client import FakeTodoistReadClient
from tests.mcp.running_core import free_port, running_app, running_core
from workers.mcp.auth.core_auth_factory import build_core_auth
from workers.mcp.auth.core_auth_settings import CoreAuthSettings
from workers.mcp.core_server_factory import build_core_middleware, build_core_server
from workers.mcp.core_tools_factory import build_core_tools
from workers.mcp.journal.denial_journal import DenialJournal
from workers.mcp.journal.json_lines_file import JsonLinesFile

OWNER_EMAIL = "owner@example.org"
STRANGER_EMAIL = "stranger@example.org"
UPSTREAM_CLIENT_ID = "core-upstream-client"
UPSTREAM_CLIENT_CREDENTIAL = "upstream-client-credential"
CLIENT_REDIRECT_URI = "http://localhost:53682/callback"
CLIENT_STATE = "client-state-1"
CSRF_INPUT = re.compile(r'name="csrf_token" value="([^"]+)"')


@dataclass
class OAuthStand:
    base_url: str
    mcp_url: str
    provider: FakeOidcProvider
    journal_file: Path


def stand_for(email: str, tmp_path: Path) -> Iterator[OAuthStand]:
    provider_port = free_port()
    provider = FakeOidcProvider(
        issuer=f"http://127.0.0.1:{provider_port}",
        client_id=UPSTREAM_CLIENT_ID,
        email=email,
    )
    journal_file = tmp_path / "requests.jsonl"
    core_port = free_port()
    with running_app(provider.app(), provider_port):
        journal = JsonLinesFile(journal_file)
        auth = build_core_auth(
            CoreAuthSettings(
                oidc_config_url=provider.config_url,
                oidc_client_id=UPSTREAM_CLIENT_ID,
                oidc_client_secret=UPSTREAM_CLIENT_CREDENTIAL,
                public_url=f"http://127.0.0.1:{core_port}",
                jwt_signing_key="core-jwt-signing-key-for-tests",
                storage_dir=tmp_path / "oauth",
                allowed_emails=frozenset({OWNER_EMAIL}),
            ),
            DenialJournal(journal),
        )
        server = build_core_server(
            build_core_tools(todoist=FakeTodoistReadClient([]), dropbox_root=tmp_path),
            auth=auth,
            middleware=build_core_middleware(journal, frozenset()),
        )
        with running_core(server, core_port) as mcp_url:
            yield OAuthStand(
                base_url=f"http://127.0.0.1:{core_port}",
                mcp_url=mcp_url,
                provider=provider,
                journal_file=journal_file,
            )


@pytest.fixture
def owner_stand(tmp_path: Path) -> Iterator[OAuthStand]:
    yield from stand_for(OWNER_EMAIL, tmp_path)


@pytest.fixture
def stranger_stand(tmp_path: Path) -> Iterator[OAuthStand]:
    yield from stand_for(STRANGER_EMAIL, tmp_path)


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge.decode().rstrip("=")


def register_client(base_url: str) -> str:
    response = httpx.post(
        f"{base_url}/register",
        json={
            "redirect_uris": [CLIENT_REDIRECT_URI],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "client_name": "oauth-test-client",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["client_id"]


def approve_consent(browser: httpx.Client, consent_url: str) -> str:
    page = browser.get(consent_url)
    [csrf_token] = CSRF_INPUT.findall(page.text)
    txn_id = parse_qs(urlparse(consent_url).query)["txn_id"][0]
    approved = browser.post(
        consent_url.split("?")[0],
        data={"txn_id": txn_id, "action": "approve", "csrf_token": csrf_token},
    )
    assert approved.status_code == 302, approved.text
    return approved.headers["location"]


def sign_in(stand: OAuthStand) -> httpx.Response:
    client_id = register_client(stand.base_url)
    verifier, challenge = pkce_pair()
    with httpx.Client(follow_redirects=False) as browser:
        authorized = browser.get(
            f"{stand.base_url}/authorize",
            params={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": CLIENT_REDIRECT_URI,
                "state": CLIENT_STATE,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "openid email",
            },
        )
        assert authorized.status_code == 302, authorized.text
        upstream_url = approve_consent(browser, authorized.headers["location"])
        assert upstream_url.startswith(stand.provider.authorization_endpoint)
        signed_in = browser.get(upstream_url)
        callback = browser.get(signed_in.headers["location"])
        assert callback.status_code == 302, callback.text
    client_redirect = urlparse(callback.headers["location"])
    query = parse_qs(client_redirect.query)
    assert client_redirect.netloc == "localhost:53682"
    assert query["state"] == [CLIENT_STATE]
    return httpx.post(
        f"{stand.base_url}/token",
        data={
            "grant_type": "authorization_code",
            "code": query["code"][0],
            "redirect_uri": CLIENT_REDIRECT_URI,
            "client_id": client_id,
            "code_verifier": verifier,
        },
    )


async def call_find_tasks(mcp_url: str, access_token: str) -> CallToolResult:
    async with (
        httpx2.AsyncClient(headers={"Authorization": f"Bearer {access_token}"}) as http,
        streamable_http_client(mcp_url, http_client=http) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        return await session.call_tool("find_tasks", {})


def journal_lines(journal_file: Path) -> list[dict[str, Any]]:
    if not journal_file.exists():
        return []
    return [
        json.loads(line)
        for line in journal_file.read_text(encoding="utf-8").splitlines()
    ]


def test_registered_client_signs_in_at_provider_and_calls_tool(
    owner_stand: OAuthStand,
):
    token_response = sign_in(owner_stand)

    assert token_response.status_code == 200, token_response.text
    result = anyio.run(
        call_find_tasks, owner_stand.mcp_url, token_response.json()["access_token"]
    )
    assert not result.is_error
    [upstream_request] = owner_stand.provider.authorize_requests
    assert upstream_request["scope"] == "openid email"
    tool_calls = [
        line
        for line in journal_lines(owner_stand.journal_file)
        if line["method"] == "tools/call"
    ]
    assert [(line["user"], line["outcome"]) for line in tool_calls] == [
        (OWNER_EMAIL, "ok")
    ]


def test_account_outside_allowlist_gets_no_core_token(stranger_stand: OAuthStand):
    token_response = sign_in(stranger_stand)

    assert token_response.status_code == 401
    assert token_response.json()["error"] == "invalid_grant"
    lines = journal_lines(stranger_stand.journal_file)
    assert [(line["method"], line["user"], line["outcome"]) for line in lines] == [
        ("auth", STRANGER_EMAIL, "denied")
    ]


def test_core_rejects_request_without_token(owner_stand: OAuthStand):
    response = httpx.post(
        owner_stand.mcp_url,
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers={"Accept": "application/json, text/event-stream"},
    )

    assert response.status_code == 401
