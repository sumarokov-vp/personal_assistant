from pydantic import Field

from src.flows.recordings.services.protocol_drafter.call_protocol_draft import (
    CallProtocolDraft,
)
from src.protocols.models.discussion_topic import DiscussionTopic


class MeetingProtocolDraft(CallProtocolDraft):
    agenda: list[str] = Field(default=[], description="Темы повестки")
    discussion: list[DiscussionTopic] = Field(
        default=[], description="По темам повестки, тезисами"
    )
