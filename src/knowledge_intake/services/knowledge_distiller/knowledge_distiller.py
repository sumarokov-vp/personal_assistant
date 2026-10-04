from contextlib import suppress
from uuid import uuid4

from pydantic import ValidationError

from src.knowledge_intake.models.accepted_letter import AcceptedLetter
from src.knowledge_intake.models.knowledge_entry import KnowledgeEntry
from src.knowledge_intake.services.entities.distill_outcome import DistillOutcome
from src.knowledge_intake.services.knowledge_distiller.distilled_answer import (
    DISTILLED_ANSWER,
    KnowledgeAnswer,
    NotKnowledgeAnswer,
)
from src.knowledge_intake.services.knowledge_distiller.protocols.i_knowledge_index import (
    IKnowledgeIndex,
)
from src.knowledge_intake.services.knowledge_distiller.protocols.i_knowledge_model import (
    IKnowledgeModel,
)
from src.knowledge_intake.services.knowledge_distiller.residual_data_check import (
    ResidualDataCheck,
)
from src.knowledge_intake.services.knowledge_distiller.untrusted_letter_frame import (
    UntrustedLetterFrame,
)

THREAD_PREFIX = "knowledge_intake"
CODE_FENCE = "```"
EMPTY_INDEX = "(база пуста)"


class KnowledgeDistiller:
    def __init__(
        self,
        model: IKnowledgeModel,
        index: IKnowledgeIndex,
        plugins: tuple[str, ...],
        frame: UntrustedLetterFrame,
        residual_check: ResidualDataCheck,
    ) -> None:
        self._model = model
        self._index = index
        self._plugins = plugins
        self._frame = frame
        self._residual_check = residual_check

    def distill(self, letter: AcceptedLetter) -> DistillOutcome:
        reply = self._model.answer(
            f"{THREAD_PREFIX}:{uuid4().hex}", self._request(letter)
        )
        answer: KnowledgeAnswer | NotKnowledgeAnswer | None = None
        with suppress(ValidationError):
            answer = DISTILLED_ANSWER.validate_json(_without_code_fence(reply))
        if answer is None:
            return DistillOutcome(refusal="ответ модели не по схеме")
        if isinstance(answer, NotKnowledgeAnswer):
            return DistillOutcome(refusal=f"не знание: {answer.reason}")
        return self._checked(answer)

    def _checked(self, answer: KnowledgeAnswer) -> DistillOutcome:
        if answer.plugin not in self._plugins or not self._index.has_plugin(
            answer.plugin
        ):
            return DistillOutcome(refusal=f"плагин {answer.plugin} знаний не принимает")
        leaked = self._residual_check.leaked(
            [
                answer.topic,
                answer.when_to_apply,
                answer.essence,
                *answer.subtleties,
                *answer.sources,
            ]
        )
        if leaked:
            return DistillOutcome(
                refusal="вычистка не удалась: в тексте остался " + ", ".join(leaked)
            )
        known_files = {line.file for line in self._index.index_lines(answer.plugin)}
        return DistillOutcome(
            entry=KnowledgeEntry(
                plugin=answer.plugin,
                topic=answer.topic,
                when_to_apply=answer.when_to_apply,
                essence=answer.essence,
                subtleties=answer.subtleties,
                sources=answer.sources,
                topic_file=answer.topic_file
                if answer.topic_file in known_files
                else None,
            )
        )

    def _request(self, letter: AcceptedLetter) -> str:
        indexes = "\n\n".join(
            f"=== {plugin}/knowledge/INDEX.md ===\n"
            f"{self._index.index_text(plugin).strip() or EMPTY_INDEX}"
            for plugin in self._plugins
        )
        return (
            "Разбери письмо по инструкции и ответь одним JSON-объектом по схеме.\n\n"
            f"Плагины, принимающие знания: {', '.join(self._plugins)}.\n\n"
            f"{indexes}\n\n"
            f"{self._frame.wrap(_letter_text(letter))}"
        )


def _letter_text(letter: AcceptedLetter) -> str:
    attachments = "".join(
        f"\n\nВложение «{attachment.filename}»:\n{attachment.text}"
        if attachment.text
        else f"\n\nВложение «{attachment.filename}» (не текст, содержимое не передано)"
        for attachment in letter.attachments
    )
    return f"Тема: {letter.subject}\n\n{letter.body}{attachments}"


def _without_code_fence(reply: str) -> str:
    text = reply.strip()
    if not text.startswith(CODE_FENCE):
        return text
    lines = text.splitlines()[1:]
    if lines and lines[-1].strip() == CODE_FENCE:
        lines = lines[:-1]
    return "\n".join(lines)
