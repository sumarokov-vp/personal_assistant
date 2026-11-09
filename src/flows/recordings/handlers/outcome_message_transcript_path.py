from typing import Any

from src.flows.recordings.services.recording_links.recording_links import (
    RecordingLinks,
)

TEXT_LINK_ENTITY = "text_link"


class OutcomeMessageTranscriptPath:
    def __init__(self, links: RecordingLinks) -> None:
        self._links = links

    def of(self, callback_query: Any) -> str | None:
        message = getattr(callback_query, "message", None)
        for entity in getattr(message, "entities", None) or []:
            if entity.type != TEXT_LINK_ENTITY or not entity.url:
                continue
            path = self._links.transcript_path_of(entity.url)
            if path is not None:
                return path
        return None
