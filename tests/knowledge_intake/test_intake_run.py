import json
from datetime import datetime
from collections.abc import Callable
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.knowledge_intake.knowledge_intake_factory import KnowledgeIntakeFactory
from src.knowledge_intake.models.mailbox_folder import MailboxFolder
from src.knowledge_intake.models.raw_letter import RawLetter
from src.knowledge_intake.models.toolkit_settings import ToolkitSettings
from src.knowledge_intake.repos.git_cli import GitCli
from src.knowledge_intake.services.intake_summary.intake_summary import IntakeSummary
from tests.knowledge_intake.conftest import (
    COMPANY_DOMAIN,
    EMPLOYEE,
    STRANGER,
    DkimKeys,
    FakeMailbox,
    ToolkitRemote,
    build_letter,
    sign,
)

ANSWERS = {
    "справка": {
        "verdict": "knowledge",
        "plugin": "mrs-finance",
        "topic": "Перевыпуск ЭЦП",
        "topic_file": "ecp-reissue.md",
        "when_to_apply": "перевыпуск ключа ЭЦП юрлица",
        "essence": "Банк при перевыпуске просит справку о полномочиях руководителя.",
        "subtleties": ["Справку заказывать после приказа о назначении"],
        "sources": ["Требования банка к перевыпуску"],
    },
    "дивиденды": {
        "verdict": "knowledge",
        "plugin": "mrs-finance",
        "topic": "Налог у источника по дивидендам",
        "topic_file": None,
        "when_to_apply": "выплата дивидендов нерезиденту",
        "essence": "Сертификат резидентства нужен до выплаты, а не после.",
        "subtleties": ["Без сертификата удерживается полная ставка"],
        "sources": [],
    },
    "спасибо": {"verdict": "not_knowledge", "reason": "благодарность без вывода"},
}


class KeywordModel:
    def answer(self, thread_id: str, request: str) -> str:
        letter = request.split("<untrusted_letter", 1)[1]
        keyword = next(word for word in ANSWERS if word in letter)
        return json.dumps(ANSWERS[keyword], ensure_ascii=False)


@pytest.fixture
def factory(
    tmp_path: Path,
    toolkit_remote: ToolkitRemote,
    txt_lookup: Callable[..., bytes | None],
) -> KnowledgeIntakeFactory:
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text(EMPLOYEE + "\n", encoding="utf-8")
    return KnowledgeIntakeFactory(
        toolkit=ToolkitSettings(
            clone_dir=tmp_path / "clone",
            remote_url=toolkit_remote.url,
            plugins=("mrs-finance",),
        ),
        allowlist_path=allowlist,
        timezone=ZoneInfo("Asia/Almaty"),
        txt_lookup=txt_lookup,
    )


def employee_letter(keys: DkimKeys, subject: str, body: str) -> bytes:
    return sign(
        build_letter(EMPLOYEE, subject=subject, body=body), keys, COMPANY_DOMAIN
    )


def test_mixed_run_merges_two_letters_and_reports_three_groups(
    factory: KnowledgeIntakeFactory,
    toolkit_remote: ToolkitRemote,
    company_keys: DkimKeys,
    tmp_path: Path,
) -> None:
    mailbox = FakeMailbox(
        [
            RawLetter(
                "1", employee_letter(company_keys, "ЭЦП", "банк попросил справка")
            ),
            RawLetter("2", employee_letter(company_keys, "Дивиденды", "про дивиденды")),
            RawLetter("3", employee_letter(company_keys, "Привет", "спасибо агенту")),
            RawLetter("4", sign(build_letter(STRANGER), company_keys, COMPANY_DOMAIN)),
        ]
    )

    report = factory.create_run(mailbox, KeywordModel()).execute()

    subjects = toolkit_remote.log("--format=%s").splitlines()
    assert subjects[:3] == [
        "chore(mrs-finance): версия после знаний — mrs-finance 0.3.1",
        "knowledge(mrs-finance): Налог у источника по дивидендам",
        "knowledge(mrs-finance): Перевыпуск ЭЦП",
    ]
    trailers = toolkit_remote.log(
        "--format=%(trailers:key=Suggested-by,valueonly)", "-n", "3"
    )
    assert trailers.split().count(f"<{EMPLOYEE}>") == 2
    knowledge_shas = toolkit_remote.log("--format=%H", "-n", "3", "--reverse").split()[
        :2
    ]
    assert [item.commit_sha for item in report.merged] == knowledge_shas
    assert mailbox.moves == {
        "1": MailboxFolder.PROCESSED,
        "2": MailboxFolder.PROCESSED,
        "3": MailboxFolder.PROCESSED,
        "4": MailboxFolder.REJECTED,
    }

    clone = tmp_path / "clone" / "plugins" / "mrs-finance"
    index = (clone / "knowledge" / "INDEX.md").read_text(encoding="utf-8")
    assert (
        "- Налог у источника по дивидендам · nalog-u-istochnika-po-dividendam.md ·"
        in index
    )
    today = datetime.now(tz=ZoneInfo("Asia/Almaty")).strftime("%d.%m.%Y")
    new_topic = (clone / "knowledge" / "nalog-u-istochnika-po-dividendam.md").read_text(
        encoding="utf-8"
    )
    assert new_topic == (
        "---\n"
        "topic: Налог у источника по дивидендам\n"
        f"date: {today}\n"
        f"source: письмо агенту {today}\n"
        f"suggested_by: Анна Тестова <{EMPLOYEE}>\n"
        "---\n\n"
        "## Суть\n\nСертификат резидентства нужен до выплаты, а не после.\n\n"
        "## Тонкости\n\n- Без сертификата удерживается полная ставка\n"
    )
    extended = (clone / "knowledge" / "ecp-reissue.md").read_text(encoding="utf-8")
    assert f"date: {today}\n" in extended
    assert "date: 01.01.2026" not in extended
    assert f"## Дополнение от {today}\n" in extended
    assert (
        "### Тонкости\n\n- Справку заказывать после приказа о назначении\n" in extended
    )
    assert "### Источники и нормы\n\n- Требования банка к перевыпуску\n" in extended
    assert '"version": "0.3.1"' in (clone / ".claude-plugin" / "plugin.json").read_text(
        encoding="utf-8"
    )

    summary = IntakeSummary().render(report)
    assert summary is not None
    assert "Влито (2):" in summary
    assert "Не принято (1):" in summary
    assert "Отклонено на входе (1):" in summary
    assert f"{STRANGER} · нет в списке допуска" in summary


class RacingModel(KeywordModel):
    def __init__(self, remote: ToolkitRemote) -> None:
        self._remote = remote

    def answer(self, thread_id: str, request: str) -> str:
        self._remote.owner_commit(
            "README.md", "соседняя правка\n", "docs: соседняя правка"
        )
        return super().answer(thread_id, request)


def test_push_rejected_by_newer_remote_is_rebased_once(
    factory: KnowledgeIntakeFactory,
    toolkit_remote: ToolkitRemote,
    company_keys: DkimKeys,
) -> None:
    mailbox = FakeMailbox(
        [RawLetter("1", employee_letter(company_keys, "ЭЦП", "справка"))]
    )

    report = factory.create_run(mailbox, RacingModel(toolkit_remote)).execute()

    assert report.publish_error is None
    assert toolkit_remote.log("--format=%s", "-n", "3").splitlines() == [
        "chore(mrs-finance): версия после знаний — mrs-finance 0.3.1",
        "knowledge(mrs-finance): Перевыпуск ЭЦП",
        "docs: соседняя правка",
    ]
    assert (
        report.merged[0].commit_sha
        == toolkit_remote.log("--format=%H", "-n", "2").split()[1]
    )


class ConflictingModel(KeywordModel):
    def __init__(self, remote: ToolkitRemote) -> None:
        self._remote = remote

    def answer(self, thread_id: str, request: str) -> str:
        index = "plugins/mrs-finance/knowledge/INDEX.md"
        current = (self._remote.owner_dir / index).read_text(encoding="utf-8")
        self._remote.owner_commit(
            index, current + "- Чужая тема · other.md · иное\n", "docs: index"
        )
        return super().answer(thread_id, request)


def test_conflicting_push_leaves_letters_unread_and_reports_failure(
    factory: KnowledgeIntakeFactory,
    toolkit_remote: ToolkitRemote,
    company_keys: DkimKeys,
) -> None:
    mailbox = FakeMailbox(
        [RawLetter("1", employee_letter(company_keys, "Дивиденды", "дивиденды"))]
    )

    report = factory.create_run(mailbox, ConflictingModel(toolkit_remote)).execute()

    assert mailbox.moves == {}
    assert report.merged == []
    summary = IntakeSummary().render(report)
    assert summary is not None
    assert "Вливание не прошло, писем осталось в ящике: 1." in summary
    assert toolkit_remote.log("--format=%s", "-n", "1").strip() == "docs: index"


def test_revert_of_knowledge_commit_restores_file(
    factory: KnowledgeIntakeFactory,
    toolkit_remote: ToolkitRemote,
    company_keys: DkimKeys,
    tmp_path: Path,
) -> None:
    mailbox = FakeMailbox(
        [RawLetter("1", employee_letter(company_keys, "Дивиденды", "дивиденды"))]
    )
    report = factory.create_run(mailbox, KeywordModel()).execute()
    clone_git = GitCli(tmp_path / "clone")

    clone_git.run_checked(
        "-c",
        "user.name=Owner",
        "-c",
        "user.email=owner@example.com",
        "revert",
        "--no-edit",
        report.merged[0].commit_sha,
    )

    knowledge = tmp_path / "clone" / "plugins" / "mrs-finance" / "knowledge"
    assert not (knowledge / "nalog-u-istochnika-po-dividendam.md").exists()
    assert "дивидендам" not in (knowledge / "INDEX.md").read_text(encoding="utf-8")


def test_empty_run_says_nothing(factory: KnowledgeIntakeFactory) -> None:
    report = factory.create_run(FakeMailbox([]), KeywordModel()).execute()

    assert IntakeSummary().render(report) is None
