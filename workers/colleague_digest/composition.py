from pathlib import Path

from src.agent_notifications.services.text_splitter import TelegramTextSplitter
from src.colleague_mail.repos import (
    PostgresColleagueMessageRepository,
    YamlColleagueDirectory,
)
from src.colleague_mail.services.digest import ColleagueDigest
from src.colleague_mail.services.digest.protocols.i_owner_notifier import (
    IOwnerNotifier,
)


def build_colleague_digest(
    database_url: str, directory_file: Path | None, notifier: IOwnerNotifier
) -> ColleagueDigest:
    return ColleagueDigest(
        journal=PostgresColleagueMessageRepository(database_url=database_url),
        directory=YamlColleagueDirectory(directory_file) if directory_file else None,
        notifier=notifier,
        splitter=TelegramTextSplitter(),
    )
