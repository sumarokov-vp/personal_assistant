import threading

from src.wiki.models.wiki_settings import WikiSettings
from src.wiki.repos.git_cli import GitCli
from src.wiki.services.wiki_path_policy.wiki_path_policy import WikiPathPolicy
from src.wiki.services.wiki_reader.wiki_reader import WikiReader
from src.wiki.services.wiki_sync.wiki_sync import WikiSync
from src.wiki.services.wiki_writer.wiki_writer import WikiWriter


class WikiFactory:
    def __init__(self, settings: WikiSettings) -> None:
        self._settings = settings
        self._lock = threading.Lock()
        self._git = GitCli(settings.wiki_dir, settings.ssh_key_path)
        self._path_policy = WikiPathPolicy(settings.wiki_dir)
        self._sync = WikiSync(
            git=self._git,
            wiki_dir=settings.wiki_dir,
            remote_url=settings.remote_url,
            branch=settings.branch,
            push_attempts=settings.push_attempts,
        )

    def create_reader(self) -> WikiReader:
        return WikiReader(
            wiki_dir=self._settings.wiki_dir,
            lock=self._lock,
            refresher=self._sync,
            path_policy=self._path_policy,
        )

    def create_writer(self) -> WikiWriter:
        return WikiWriter(
            lock=self._lock,
            publisher=self._sync,
            path_policy=self._path_policy,
            git=self._git,
            author_name=self._settings.author_name,
            author_email=self._settings.author_email,
        )
