import shutil
from pathlib import Path

import pytest
from pypdf import PdfWriter

from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary

FIXTURES = Path(__file__).parent / "fixtures"
ITINERARY_NAME = "Itinerary_ALA_CNX_12-11-2026_000000000000.pdf"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def dropbox_root(tmp_path: Path) -> Path:
    root = tmp_path / "Dropbox"
    outside = tmp_path / "outside"
    _write(outside / "secret.txt", "за пределами Dropbox")

    _write(root / "Vault" / "secret.md", "содержимое волта")
    _write(root / "vault_selftest_3544" / "probe.txt", "самопроверка")
    _write(root / "01_work" / "client" / "contract.txt", "клиентский договор")
    _write(root / "03_home" / "07_ecp" / "egov.kz" / "AUTH_RSA.p12", "ключ")
    _write(root / "03_home" / "07_ecp" / "egov.kz" / "password.md.gpg", "пароль")
    _write(root / "03_home" / "07_ecp" / "readme.md", "ЭЦП НУЦ РК")
    _write(root / "03_home" / "07_ecp" / "backup_AUTH.P12", "копия ключа")
    _write(
        root / "03_home" / "01_personal_docs" / "passport.txt", "паспорт, срок до 2031"
    )
    _write(root / "03_home" / "01_personal_docs" / "notes.md", "# Заметки")
    _write(root / "03_home" / "01_personal_docs" / "data.json", '{"a": 1}')
    _write(root / "03_home" / "01_personal_docs" / "table.csv", "a,b\n1,2\n")
    _write(root / "03_home" / "01_personal_docs" / "photo.heic", "картинка")
    (root / "03_home" / "09_travel" / "thailand_2026-11").mkdir(parents=True)
    _write(root / "Apps" / "HealthFit" / "ride.fit", "тренировка")
    _write(root / ".dropbox.cache" / "copy.txt", "кэш")
    shutil.copy(FIXTURES / ITINERARY_NAME, root / ITINERARY_NAME)

    scan = PdfWriter()
    scan.add_blank_page(width=200, height=200)
    scan.write(root / "scan.pdf")

    (root / "link_outside").symlink_to(outside, target_is_directory=True)
    (root / "link_outside.txt").symlink_to(outside / "secret.txt")
    (root / "link_to_vault").symlink_to(root / "Vault", target_is_directory=True)
    (root / "innocent.txt").symlink_to(root / "03_home" / "07_ecp" / "backup_AUTH.P12")
    return root


@pytest.fixture
def boundary(dropbox_root: Path) -> DropboxBoundary:
    return DropboxBoundary(dropbox_root, DropboxAccessPolicy())
