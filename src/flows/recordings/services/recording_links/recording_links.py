from pathlib import PurePosixPath
from urllib.parse import parse_qs, quote, unquote, urlsplit

STORAGE_HOME_URL = "https://www.dropbox.com/home"
STORAGE_HOST = "www.dropbox.com"
STORAGE_HOME_PATH = "/home"
PREVIEW_PARAMETER = "preview"


class RecordingLinks:
    def transcript_url(self, transcript_path: str) -> str:
        path = PurePosixPath(transcript_path)
        folder = "" if path.parent == PurePosixPath(".") else path.parent.as_posix()
        return f"{STORAGE_HOME_URL}/{quote(folder)}?{PREVIEW_PARAMETER}={quote(path.name, safe='')}"

    def transcript_path_of(self, url: str) -> str | None:
        parts = urlsplit(url)
        names = parse_qs(parts.query).get(PREVIEW_PARAMETER)
        folder = unquote(parts.path)
        if parts.netloc != STORAGE_HOST or not names:
            return None
        if folder != STORAGE_HOME_PATH and not folder.startswith(
            f"{STORAGE_HOME_PATH}/"
        ):
            return None
        relative_folder = folder.removeprefix(STORAGE_HOME_PATH).strip("/")
        return (
            str(PurePosixPath(relative_folder, names[0]))
            if relative_folder
            else names[0]
        )
