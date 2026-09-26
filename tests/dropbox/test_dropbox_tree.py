import pytest

from src.dropbox.services.boundary.dropbox_access_denied_error import (
    DropboxAccessDeniedError,
)
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.tree.dropbox_tree import DropboxTree


def test_tree_counts_visible_files_only(boundary: DropboxBoundary):
    tree = DropboxTree(boundary).build(depth=1)

    assert [folder.name for folder in tree.folders] == ["03_home", "Apps"]
    assert tree.file_count == 3
    assert tree.total_file_count == 3 + 7 + 1
    home = tree.folders[0]
    assert home.path == "03_home"
    assert home.folders == []
    assert home.total_file_count == 7


def test_tree_of_subfolder_lists_files_when_asked(boundary: DropboxBoundary):
    tree = DropboxTree(boundary).build("03_home", depth=2, include_files=True)

    ecp = next(folder for folder in tree.folders if folder.name == "07_ecp")
    assert ecp.files == ["backup_AUTH.P12", "readme.md"]
    assert ecp.folders == []
    travel = next(folder for folder in tree.folders if folder.name == "09_travel")
    assert travel.folders[0].path == "03_home/09_travel/thailand_2026-11"


def test_tree_of_closed_folder_is_denied(boundary: DropboxBoundary):
    with pytest.raises(DropboxAccessDeniedError):
        DropboxTree(boundary).build("01_work")
