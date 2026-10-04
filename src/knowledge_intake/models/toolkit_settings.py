from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToolkitSettings:
    clone_dir: Path
    remote_url: str
    plugins: tuple[str, ...]
    ssh_key_path: Path | None = None
    branch: str = "main"
    author_name: str = "Knowledge Intake"
    author_email: str = "knowledge-intake@users.noreply.github.com"
