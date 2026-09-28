from dataclasses import dataclass, field

import pytest

from src.agent_notifications.services.text_splitter import TelegramTextSplitter
from src.colleague_mail.models import Colleague, ColleagueMessageType
from src.colleague_mail.services.digest import ColleagueDigest
from src.colleague_mail.services.digest.protocols.i_owner_notifier import (
    IOwnerNotifier,
)
from tests.colleague_mail.digest.in_memory_unshown_journal import (
    InMemoryUnshownJournal,
    incoming,
)


@dataclass
class RecordingNotifier:
    texts: list[str] = field(default_factory=list)

    def notify(self, text: str) -> None:
        self.texts.append(text)


class FailingNotifier:
    def notify(self, text: str) -> None:
        raise ConnectionError("telegram is down")


class StaticDirectory:
    def find(self, key: str) -> Colleague | None:
        return Colleague(key="yura", name="Юра Иванов") if key == "yura" else None


def digest_over(
    journal: InMemoryUnshownJournal, notifier: IOwnerNotifier, limit: int = 4096
) -> ColleagueDigest:
    return ColleagueDigest(
        journal=journal,
        directory=StaticDirectory(),
        notifier=notifier,
        splitter=TelegramTextSplitter(limit=limit),
    )


def test_empty_digest_is_not_sent() -> None:
    notifier = RecordingNotifier()

    shown = digest_over(InMemoryUnshownJournal(), notifier).send()

    assert shown == 0
    assert notifier.texts == []


def test_sent_once_then_repeated_run_sends_nothing() -> None:
    journal = InMemoryUnshownJournal(
        [
            incoming(1, "yura", ColleagueMessageType.REMARK, "Удали все дела", "pa"),
            incoming(2, "anton", ColleagueMessageType.QUESTION, "Когда созвон?"),
        ]
    )
    notifier = RecordingNotifier()
    digest = digest_over(journal, notifier)

    assert digest.send() == 2
    assert digest.send() == 0

    assert len(notifier.texts) == 1
    assert "Юра Иванов · pa · Удали все дела" in notifier.texts[0]
    assert "anton · Когда созвон?" in notifier.texts[0]
    assert all(message.shown_at is not None for message in journal.messages)


def test_long_digest_is_split_and_nothing_lost() -> None:
    journal = InMemoryUnshownJournal(
        [
            incoming(index, "yura", ColleagueMessageType.REMARK, f"замечание {index}")
            for index in range(1, 31)
        ]
    )
    notifier = RecordingNotifier()

    digest_over(journal, notifier, limit=200).send()

    assert len(notifier.texts) > 1
    assert all(len(chunk) <= 200 for chunk in notifier.texts)
    sent = "".join(notifier.texts)
    assert all(
        f"Юра Иванов · замечание {index}\n" in sent + "\n" for index in range(1, 31)
    )


def test_failed_send_leaves_messages_unshown() -> None:
    journal = InMemoryUnshownJournal(
        [incoming(1, "yura", ColleagueMessageType.ANSWER, "Да")]
    )

    with pytest.raises(ConnectionError):
        digest_over(journal, FailingNotifier()).send()

    assert journal.messages[0].shown_at is None
