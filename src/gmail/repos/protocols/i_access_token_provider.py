from typing import Protocol


class IAccessTokenProvider(Protocol):
    def access_token(self) -> str: ...
