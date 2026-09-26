from pathlib import Path

from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.files.overflow.overflow_folder import OverflowFolder
from src.files.work_folder.work_folder import WorkFolder


def test_place_creates_folder_and_never_overwrites(tmp_path: Path):
    dropbox = tmp_path / "Dropbox"
    dropbox.mkdir()
    work_folder = WorkFolder(tmp_path / "work")
    overflow = OverflowFolder(
        DropboxBoundary(dropbox, DropboxAccessPolicy()), work_folder
    )
    first = work_folder.put(b"one", "video.mp4", "video/mp4", "gmail")
    second = work_folder.put(b"two", "video.mp4", "video/mp4", "gmail")

    assert overflow.place(first) == "Personal Assistant/video.mp4"
    assert overflow.place(second) == "Personal Assistant/video (2).mp4"
    assert (dropbox / "Personal Assistant" / "video (2).mp4").read_bytes() == b"two"
