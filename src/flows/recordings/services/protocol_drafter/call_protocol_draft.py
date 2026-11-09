from pydantic import BaseModel, Field

from src.protocols.models.protocol_action import ProtocolAction


class CallProtocolDraft(BaseModel):
    title: str = Field(min_length=1, description="Подзаголовок: «<Клиент>: <тема>»")
    date: str = Field(description="Дата разговора, ДД.ММ.ГГГГ")
    parties: dict[str, list[str]] = Field(
        default={}, description="Сторона → участники (имя или роль)"
    )
    agreements: list[str] = Field(
        default=[], description="Решения встречи или договорённости звонка"
    )
    actions: list[ProtocolAction] = Field(
        default=[], description="Поручения: what — что, who — кто, due — срок"
    )
    open_questions: list[str] = Field(
        default=[], description="Что не решено и к кому вопрос"
    )
