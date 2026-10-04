from typing import Any

import anyio
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from workers.mcp.auth.allowlist_token_verifier import AllowlistTokenVerifier
from workers.mcp.auth.email_allowlist import EmailAllowlist

OWNER_EMAIL = "owner@example.org"


class RecordedDenials:
    def __init__(self) -> None:
        self.users: list[str | None] = []

    def record_denied(self, user: str | None) -> None:
        self.users.append(user)


def verify(claims: dict[str, Any]) -> tuple[bool, list[str | None]]:
    denials = RecordedDenials()
    verifier = AllowlistTokenVerifier(
        identity=StaticTokenVerifier({"t": {"client_id": "c", **claims}}),
        allowlist=EmailAllowlist({OWNER_EMAIL}),
        denials=denials,
    )
    verified = anyio.run(verifier.verify_token, "t")
    return verified is not None, denials.users


def test_listed_verified_email_is_admitted_case_insensitively():
    assert verify({"email": "Owner@Example.org", "email_verified": True}) == (
        True,
        [],
    )


def test_unverified_email_is_denied_even_when_listed():
    assert verify({"email": OWNER_EMAIL, "email_verified": False}) == (
        False,
        [OWNER_EMAIL],
    )


def test_unlisted_email_is_denied():
    assert verify({"email": "x@example.org", "email_verified": True}) == (
        False,
        ["x@example.org"],
    )
