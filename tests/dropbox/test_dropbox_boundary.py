from pathlib import Path

import pytest

from src.dropbox.services.boundary.dropbox_access_denied_error import (
    DropboxAccessDeniedError,
)
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.reader.dropbox_reader import DropboxReader


@pytest.mark.parametrize(
    "path",
    [
        "Vault/secret.md",
        "vault/secret.md",
        "Vault",
        "vault_selftest_3544/probe.txt",
        "03_home/07_ecp/egov.kz/AUTH_RSA.p12",
        "03_home/07_ecp/egov.kz/password.md.gpg",
        "03_home/07_ecp/backup_AUTH.P12",
        "innocent.txt",
        "link_outside/secret.txt",
        "link_outside.txt",
        "link_to_vault/secret.md",
        "../outside/secret.txt",
        "03_home/../Vault/secret.md",
        ".dropbox.cache/copy.txt",
    ],
)
def test_read_of_closed_path_is_denied(boundary: DropboxBoundary, path: str):
    with pytest.raises(DropboxAccessDeniedError):
        DropboxReader(boundary).read(path)


def test_absolute_path_outside_root_is_denied(
    boundary: DropboxBoundary, tmp_path: Path
):
    with pytest.raises(DropboxAccessDeniedError):
        boundary.resolve(str(tmp_path / "outside" / "secret.txt"))


def test_absolute_path_inside_root_resolves(
    boundary: DropboxBoundary, dropbox_root: Path
):
    resolved = boundary.resolve(str(dropbox_root / "03_home" / "07_ecp" / "readme.md"))
    assert boundary.relative(resolved) == "03_home/07_ecp/readme.md"


def test_root_listing_hides_closed_entries_and_outside_links(boundary: DropboxBoundary):
    names = [child.name for child in boundary.visible_children(boundary.root)]
    assert names == [
        "01_work",
        "03_home",
        "Apps",
        "innocent.txt",
        "Itinerary_ALA_CNX_12-11-2026_000000000000.pdf",
        "scan.pdf",
    ]


def test_key_file_is_listed_by_name(boundary: DropboxBoundary):
    ecp = boundary.resolve("03_home/07_ecp")
    assert [child.name for child in boundary.visible_children(ecp)] == [
        "backup_AUTH.P12",
        "readme.md",
    ]


def test_work_folder_is_readable(boundary: DropboxBoundary):
    text = DropboxReader(boundary).read("01_work/client/contract.txt")

    assert text.text == "клиентский договор"
