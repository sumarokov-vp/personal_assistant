from pathlib import Path

import pytest

from src.agent_notifications.services.dropbox_file_store import DropboxAgentFileStore
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary

LIMIT = 100


@pytest.fixture
def root(tmp_path: Path) -> Path:
    dropbox = tmp_path / "dropbox"
    (dropbox / "Personal Assistant" / "agents").mkdir(parents=True)
    return dropbox


@pytest.fixture
def store(root: Path) -> DropboxAgentFileStore:
    return DropboxAgentFileStore(
        dropbox=DropboxBoundary(root=root, policy=DropboxAccessPolicy()),
        size_limit_bytes=LIMIT,
    )


def test_reads_file_inside_agents_folder(
    store: DropboxAgentFileStore, root: Path
) -> None:
    (root / "Personal Assistant/agents/a.pdf").write_bytes(b"pdf")

    assert store.refusal("Personal Assistant/agents/a.pdf") is None
    assert store.read("Personal Assistant/agents/a.pdf") == b"pdf"
    assert store.read("/Personal Assistant/agents/a.pdf") == b"pdf"


def test_missing_file_is_not_refused_but_reads_as_none(
    store: DropboxAgentFileStore,
) -> None:
    assert store.refusal("Personal Assistant/agents/gone.pdf") is None
    assert store.read("Personal Assistant/agents/gone.pdf") is None


@pytest.mark.parametrize(
    "path",
    [
        "Personal Assistant/a.pdf",
        "Other/agents/a.pdf",
        "Personal Assistant/agents",
        "Personal Assistant/agents/../a.pdf",
        "Personal Assistant/agents/../../outside.pdf",
    ],
)
def test_refuses_paths_outside_agents_folder(
    store: DropboxAgentFileStore, path: str
) -> None:
    assert store.refusal(path) is not None


def test_refuses_symlinked_file(store: DropboxAgentFileStore, root: Path) -> None:
    (root / "secret.pdf").write_bytes(b"secret")
    (root / "Personal Assistant/agents/link.pdf").symlink_to(root / "secret.pdf")

    assert store.refusal("Personal Assistant/agents/link.pdf") is not None


def test_refuses_path_through_symlinked_folder(
    store: DropboxAgentFileStore, root: Path
) -> None:
    (root / "Private").mkdir()
    (root / "Private/secret.pdf").write_bytes(b"secret")
    (root / "Personal Assistant/agents/private").symlink_to(root / "Private")

    assert store.refusal("Personal Assistant/agents/private/secret.pdf") is not None


def test_refuses_file_over_size_limit(store: DropboxAgentFileStore, root: Path) -> None:
    (root / "Personal Assistant/agents/big.bin").write_bytes(b"x" * (LIMIT + 1))
    (root / "Personal Assistant/agents/edge.bin").write_bytes(b"x" * LIMIT)

    assert store.refusal("Personal Assistant/agents/big.bin") is not None
    assert store.refusal("Personal Assistant/agents/edge.bin") is None
