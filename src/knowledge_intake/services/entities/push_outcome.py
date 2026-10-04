from dataclasses import dataclass, field


@dataclass(frozen=True)
class PushOutcome:
    pushed: bool
    commit_shas: list[str] = field(default_factory=list)
    versions: dict[str, str] = field(default_factory=dict)
    error: str | None = None
