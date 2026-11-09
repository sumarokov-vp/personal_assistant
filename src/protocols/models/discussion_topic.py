from pydantic import BaseModel, Field


class DiscussionTopic(BaseModel):
    topic: str = Field(min_length=1)
    points: list[str]
