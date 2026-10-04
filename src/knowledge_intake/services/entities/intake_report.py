from dataclasses import dataclass, field


@dataclass(frozen=True)
class MergedLetter:
    plugin: str
    topic: str
    sender: str
    commit_sha: str


@dataclass(frozen=True)
class DeclinedLetter:
    sender: str
    subject: str
    reason: str


@dataclass(frozen=True)
class RejectedLetter:
    address: str
    reason: str


@dataclass
class IntakeReport:
    merged: list[MergedLetter] = field(default_factory=list)
    declined: list[DeclinedLetter] = field(default_factory=list)
    rejected: list[RejectedLetter] = field(default_factory=list)
    versions: dict[str, str] = field(default_factory=dict)
    publish_error: str | None = None
    unpublished: int = 0

    def is_empty(self) -> bool:
        return not (self.merged or self.declined or self.rejected or self.publish_error)
