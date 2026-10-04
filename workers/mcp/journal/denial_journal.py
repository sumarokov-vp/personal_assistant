import json
from datetime import UTC, datetime

from workers.mcp.journal.journal_entry import JournalEntry
from workers.mcp.journal.protocols.i_journal_sink import IJournalSink

AUTH_METHOD = "auth"


class DenialJournal:
    def __init__(self, sink: IJournalSink) -> None:
        self._sink = sink

    def record_denied(self, user: str | None) -> None:
        entry = JournalEntry(
            time=datetime.now(UTC),
            method=AUTH_METHOD,
            client=None,
            headers={},
            meta=None,
            tool=None,
            project=None,
            project_source=None,
            user=user,
            outcome="denied",
        )
        self._sink.append(
            json.dumps(entry.model_dump(mode="json"), ensure_ascii=False, default=str)
        )
