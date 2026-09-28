from pathlib import Path

from src.wiki.repos.git_cli import GitCli

GIT_IDENTITY = (
    "-c",
    "user.name=Owner",
    "-c",
    "user.email=owner@example.com",
    "-c",
    "commit.gpgsign=false",
)


def agent_markdown(name: str, description: str, instruction: str) -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n\n{instruction}\n"


def write_agent(layer_dir: Path, file_name: str, content: str) -> Path:
    path = layer_dir / "agents" / file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def git(repo: Path, *args: str) -> str:
    return GitCli(repo).run_checked(*GIT_IDENTITY, *args).strip()


def commit_all(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")
