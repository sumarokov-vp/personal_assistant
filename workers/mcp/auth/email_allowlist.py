from collections.abc import Mapping, Set
from typing import Any

EMAIL_CLAIM = "email"
EMAIL_VERIFIED_CLAIM = "email_verified"


class EmailAllowlist:
    def __init__(self, emails: Set[str]) -> None:
        self._emails = frozenset(email.lower() for email in emails)

    def admits(self, claims: Mapping[str, Any]) -> bool:
        email = claims.get(EMAIL_CLAIM)
        return (
            isinstance(email, str)
            and email.lower() in self._emails
            and claims.get(EMAIL_VERIFIED_CLAIM) is True
        )
