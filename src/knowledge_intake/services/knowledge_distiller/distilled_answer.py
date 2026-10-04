from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class KnowledgeAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Literal["knowledge"]
    plugin: str = Field(min_length=1, max_length=64)
    topic: str = Field(min_length=1, max_length=120)
    topic_file: str | None = Field(default=None, max_length=120)
    when_to_apply: str = Field(min_length=1, max_length=300)
    essence: str = Field(min_length=1, max_length=2_000)
    subtleties: list[Annotated[str, Field(min_length=1, max_length=2_000)]] = Field(
        default_factory=list, max_length=30
    )
    sources: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        default_factory=list, max_length=30
    )


class NotKnowledgeAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Literal["not_knowledge"]
    reason: str = Field(min_length=1, max_length=500)


type DistilledAnswer = Annotated[
    KnowledgeAnswer | NotKnowledgeAnswer, Field(discriminator="verdict")
]

DISTILLED_ANSWER: TypeAdapter[KnowledgeAnswer | NotKnowledgeAnswer] = TypeAdapter(
    DistilledAnswer
)
