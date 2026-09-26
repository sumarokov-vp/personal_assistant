from dataclasses import dataclass


@dataclass(frozen=True)
class WikiWriteResult:
    path: str
    changed: bool
    commit_sha: str
