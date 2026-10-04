from enum import StrEnum


class DkimResult(StrEnum):
    SIGNED = "signed"
    NO_SIGNATURE = "no_signature"
    OTHER_DOMAIN = "other_domain"
    INVALID = "invalid"
