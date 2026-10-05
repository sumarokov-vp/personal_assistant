import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.knowledge_intake import IntakeSummary, KnowledgeIntakeFactory, ToolkitSettings
from src.knowledge_intake.models.raw_letter import RawLetter
from tests.knowledge_intake.conftest import (
    COMPANY_DOMAIN,
    EMPLOYEE,
    DkimKeys,
    FakeMailbox,
    ToolkitRemote,
    build_letter,
    sign,
)
from workers.knowledge_intake.ai_knowledge_model import AiKnowledgeModel
from workers.knowledge_intake.intake_run_line import RUN_LINE_PREFIX, IntakeRunLine
from workers.knowledge_intake.knowledge_intake_job import KnowledgeIntakeJob

KNOWLEDGE = {
    "verdict": "knowledge",
    "plugin": "mrs-finance",
    "topic": "Перевыпуск ЭЦП",
    "topic_file": "ecp-reissue.md",
    "when_to_apply": "перевыпуск ключа ЭЦП юрлица",
    "essence": "Банк при перевыпуске просит справку о полномочиях руководителя.",
    "subtleties": ["Справку заказывать после приказа о назначении"],
    "sources": ["Требования банка к перевыпуску"],
}


@dataclass(frozen=True)
class CannedAnswer:
    content: str | None


@dataclass
class CannedConversation:
    reply: str | None
    threads: list[str] = field(default_factory=list)

    def process_message(self, thread_id: str, user_message: str) -> CannedAnswer:
        self.threads.append(thread_id)
        return CannedAnswer(self.reply)


@dataclass
class RecordingNotifier:
    texts: list[str] = field(default_factory=list)

    def notify(self, text: str) -> None:
        self.texts.append(text)


@pytest.fixture
def job_and_notifier(
    tmp_path: Path,
    toolkit_remote: ToolkitRemote,
    txt_lookup: Callable[..., bytes | None],
) -> tuple[KnowledgeIntakeJob, RecordingNotifier]:
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text(EMPLOYEE + "\n", encoding="utf-8")
    notifier = RecordingNotifier()
    job = KnowledgeIntakeJob(
        runs=KnowledgeIntakeFactory(
            toolkit=ToolkitSettings(
                clone_dir=tmp_path / "clone",
                remote_url=toolkit_remote.url,
                plugins=("mrs-finance",),
            ),
            allowlist_path=allowlist,
            timezone=ZoneInfo("Asia/Almaty"),
            txt_lookup=txt_lookup,
        ),
        summary=IntakeSummary(),
        run_line=IntakeRunLine(),
        notifier=notifier,
    )
    return job, notifier


def test_merged_letter_reaches_owner_and_run_line_is_logged(
    job_and_notifier: tuple[KnowledgeIntakeJob, RecordingNotifier],
    company_keys: DkimKeys,
    caplog: pytest.LogCaptureFixture,
) -> None:
    job, notifier = job_and_notifier
    letter = sign(build_letter(EMPLOYEE), company_keys, COMPANY_DOMAIN)
    model = AiKnowledgeModel(
        CannedConversation(json.dumps(KNOWLEDGE, ensure_ascii=False))
    )

    with caplog.at_level("INFO"):
        job.execute(FakeMailbox([RawLetter(uid="1", content=letter)]), model)

    assert len(notifier.texts) == 1
    assert "Влито (1)" in notifier.texts[0]
    run_lines = [
        r.message for r in caplog.records if r.message.startswith(RUN_LINE_PREFIX)
    ]
    assert len(run_lines) == 1
    assert "fetched=1 merged=1 declined=0 rejected=0 push=ok" in run_lines[0]


def test_empty_run_is_silent_for_owner_but_logged(
    job_and_notifier: tuple[KnowledgeIntakeJob, RecordingNotifier],
    caplog: pytest.LogCaptureFixture,
) -> None:
    job, notifier = job_and_notifier

    with caplog.at_level("INFO"):
        text = job.execute(FakeMailbox([]), AiKnowledgeModel(CannedConversation(None)))

    assert text is None
    assert notifier.texts == []
    assert any(
        r.message.startswith(f"{RUN_LINE_PREFIX} ")
        and "fetched=0 merged=0 declined=0 rejected=0 push=ok" in r.message
        for r in caplog.records
    )
