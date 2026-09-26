import json
import shutil
from pathlib import Path

import pytest
from ai_framework.entities.tool_context import ToolContext

from src.ai_tools.dropbox_read import DropboxReadTool
from src.ai_tools.dropbox_read.tool import DropboxReadInput
from src.ai_tools.dropbox_search import DropboxSearchTool
from src.ai_tools.dropbox_search.tool import DropboxSearchInput
from src.ai_tools.dropbox_tree import DropboxTreeTool
from src.ai_tools.dropbox_tree.tool import DropboxTreeInput
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.reader.dropbox_reader import DropboxReader
from src.dropbox.services.search.dropbox_search import DropboxSearch
from src.dropbox.services.tree.dropbox_tree import DropboxTree

ITINERARY = (
    Path(__file__).parents[2]
    / "dropbox"
    / "fixtures"
    / "Itinerary_ALA_CNX_12-11-2026_000000000000.pdf"
)
CONTEXT = ToolContext({"chat_id": 1, "user_id": 1})


@pytest.fixture
def boundary(tmp_path: Path) -> DropboxBoundary:
    (tmp_path / "Vault").mkdir()
    (tmp_path / "Vault" / "secret.md").write_text("волт", encoding="utf-8")
    (tmp_path / "03_home" / "09_travel").mkdir(parents=True)
    (tmp_path / "photo.heic").write_bytes(b"heic")
    shutil.copy(ITINERARY, tmp_path / ITINERARY.name)
    return DropboxBoundary(tmp_path, DropboxAccessPolicy())


def test_search_and_read_itinerary(boundary: DropboxBoundary) -> None:
    found = json.loads(
        DropboxSearchTool(DropboxSearch(boundary)).execute(
            DropboxSearchInput(query="itinerary"), CONTEXT
        )
    )
    path = found["hits"][0]["path"]
    read = json.loads(
        DropboxReadTool(DropboxReader(boundary)).execute(
            DropboxReadInput(path=path), CONTEXT
        )
    )
    assert "12.11.2026" in read["text"]
    assert "error" not in read


@pytest.mark.parametrize("path", ["Vault", "Vault/secret.md", "photo.heic", "nope.txt"])
def test_read_refusal_is_error_for_model(boundary: DropboxBoundary, path: str) -> None:
    result = json.loads(
        DropboxReadTool(DropboxReader(boundary)).execute(
            DropboxReadInput(path=path), CONTEXT
        )
    )
    assert result["error"]


def test_tree_and_search_refuse_hidden(boundary: DropboxBoundary) -> None:
    tree = json.loads(
        DropboxTreeTool(DropboxTree(boundary)).execute(
            DropboxTreeInput(path="Vault"), CONTEXT
        )
    )
    search = json.loads(
        DropboxSearchTool(DropboxSearch(boundary)).execute(
            DropboxSearchInput(query="secret", within="Vault"), CONTEXT
        )
    )
    assert tree["error"]
    assert search["error"]
