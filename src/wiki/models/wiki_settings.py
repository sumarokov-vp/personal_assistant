from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WikiSettings:
    wiki_dir: Path
    remote_url: str
    ssh_key_path: Path | None = None
    branch: str = "main"
    author_name: str = "Personal Assistant"
    author_email: str = "personal-assistant@users.noreply.github.com"
    push_attempts: int = 3
