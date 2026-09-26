from dataclasses import dataclass


@dataclass(frozen=True)
class GmailCredentials:
    client_id: str
    client_secret: str
    refresh_token: str
