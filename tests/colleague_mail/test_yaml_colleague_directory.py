from pathlib import Path

import pytest
from pydantic import ValidationError

from src.colleague_mail.models import Colleague
from src.colleague_mail.repos import YamlColleagueDirectory


def directory(tmp_path: Path, content: str) -> YamlColleagueDirectory:
    path = tmp_path / "directory.yaml"
    path.write_text(content, encoding="utf-8")
    return YamlColleagueDirectory(path)


def test_reads_key_mapping(tmp_path: Path) -> None:
    colleagues = directory(
        tmp_path,
        "sumarokov: {name: Владимир, editor: true}\nyura:\n  name: Юра\n",
    )

    assert colleagues.colleagues() == [
        Colleague(key="sumarokov", name="Владимир", editor=True),
        Colleague(key="yura", name="Юра", editor=False),
    ]
    assert colleagues.find("yura") == Colleague(key="yura", name="Юра", editor=False)
    assert colleagues.find("anton") is None


def test_empty_file_is_empty_directory(tmp_path: Path) -> None:
    assert directory(tmp_path, "").colleagues() == []


@pytest.mark.parametrize(
    "content", ["yura: {editor: true}\n", "Юра Петров: {name: Юра}\n"]
)
def test_invalid_entry_is_an_error(tmp_path: Path, content: str) -> None:
    with pytest.raises(ValidationError):
        directory(tmp_path, content).colleagues()
