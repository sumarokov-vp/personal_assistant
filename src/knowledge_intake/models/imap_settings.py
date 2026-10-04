from dataclasses import dataclass

IMAPS_PORT = 993


@dataclass(frozen=True)
class ImapSettings:
    host: str
    user: str
    password: str
    port: int = IMAPS_PORT
    inbox: str = "INBOX"
    timeout_seconds: float = 60.0
