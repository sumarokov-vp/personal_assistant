import os
import time
from pathlib import Path

import pytest

from src.files.sweeper.sweeper import Sweeper

HOUR = 60 * 60


def _file(path: Path, hours_old: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")
    stamp = time.time() - hours_old * HOUR
    os.utime(path, (stamp, stamp))
    return path


def _age(path: Path, hours_old: float) -> None:
    stamp = time.time() - hours_old * HOUR
    os.utime(path, (stamp, stamp), follow_symlinks=False)


@pytest.fixture
def dropbox(tmp_path: Path) -> Path:
    return tmp_path / "Dropbox"


@pytest.fixture
def overflow(dropbox: Path) -> Path:
    return dropbox / "Personal Assistant"


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
    return tmp_path / "work"


def test_removes_files_older_than_a_day_in_both_roots(work_dir: Path, overflow: Path):
    old_work = _file(work_dir / "a1b2c3d4" / "ticket.pdf", 25)
    fresh_work = _file(work_dir / "0000ffff" / "scan.png", 23)
    old_overflow = _file(overflow / "video.mp4", 25)
    fresh_overflow = _file(overflow / "archive.zip", 23)
    _age(work_dir / "a1b2c3d4", 25)

    Sweeper([work_dir, overflow]).sweep()

    assert not old_work.exists()
    assert not old_overflow.exists()
    assert not (work_dir / "a1b2c3d4").exists()
    assert fresh_work.read_bytes() == b"x"
    assert fresh_overflow.read_bytes() == b"x"
    assert work_dir.is_dir()
    assert overflow.is_dir()


def test_leaves_rest_of_dropbox_and_symlink_targets(
    tmp_path: Path, dropbox: Path, overflow: Path
):
    neighbour = _file(dropbox / "03_home" / "old_contract.pdf", 25)
    outside_file = _file(tmp_path / "outside" / "passport.pdf", 25)
    outside_dir_file = _file(tmp_path / "outside_dir" / "old.txt", 25)
    overflow.mkdir(parents=True)
    (overflow / "link.pdf").symlink_to(outside_file)
    (overflow / "link_dir").symlink_to(
        outside_dir_file.parent, target_is_directory=True
    )
    (overflow / "to_neighbour").symlink_to(neighbour.parent, target_is_directory=True)
    for link in ("link.pdf", "link_dir", "to_neighbour"):
        _age(overflow / link, 25)

    Sweeper([overflow]).sweep()

    assert neighbour.exists()
    assert outside_file.exists()
    assert outside_dir_file.exists()
    assert (overflow / "link.pdf").is_symlink()


def test_symlinked_root_is_not_swept(tmp_path: Path):
    real = _file(tmp_path / "real" / "old.txt", 25)
    root = tmp_path / "root"
    root.symlink_to(real.parent, target_is_directory=True)

    assert Sweeper([root]).sweep() == []
    assert real.exists()


def test_fresh_empty_directory_survives(work_dir: Path):
    (work_dir / "a1b2c3d4").mkdir(parents=True)

    Sweeper([work_dir]).sweep()

    assert (work_dir / "a1b2c3d4").is_dir()


def test_missing_root_is_skipped(tmp_path: Path):
    assert Sweeper([tmp_path / "absent"]).sweep() == []
