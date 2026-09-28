from enum import StrEnum


class RelinkStart(StrEnum):
    STARTED = "started"
    RUNNING = "running"
    COOLDOWN = "cooldown"
    NO_PHONE = "no_phone"
