from enum import StrEnum


class RemoteMediaState(StrEnum):
    CACHED = "cached"
    ON_REQUEST = "on_request"
    EXPIRED = "expired"
    NO_LINK = "no_link"
