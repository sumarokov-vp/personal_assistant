from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, Field

from src.ai_tools.protocol_make.protocols.i_protocol_maker import IProtocolMaker
from src.protocols.models.discussion_topic import DiscussionTopic
from src.protocols.models.protocol_action import ProtocolAction
from src.protocols.models.protocol_content import ProtocolContent
from src.protocols.models.protocol_kind import ProtocolKind


class ProtocolMakeInput(ProtocolContent):
    kind: ProtocolKind = Field(
        description="meeting — протокол встречи, call — протокол звонка"
    )
    title: str = Field(min_length=1, description="Подзаголовок: «<Клиент>: <тема>»")
    date: str = Field(description="Дата разговора, ДД.ММ.ГГГГ")
    parties: dict[str, list[str]] = Field(
        default={}, description="Сторона → участники (имя или роль)"
    )
    agenda: list[str] = Field(default=[], description="Только meeting: темы повестки")
    discussion: list[DiscussionTopic] = Field(
        default=[], description="Только meeting: по темам повестки, тезисами"
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


class ProtocolMakeTool(BaseTool):
    name: ClassVar[str] = "protocol_make"
    description: ClassVar[str] = (
        "Собирает протокол встречи (kind=meeting) или звонка (kind=call) в PDF по "
        "шаблону Smartist и кладёт PDF и исходник .typ в папку «Записи разговоров» "
        "хранилища. Ответ: pdf_path и typ_path — пути от корня хранилища. "
        "Встреча: участники по сторонам, повестка, обсуждение по темам, решения, "
        "поручения, открытые вопросы. Звонок короче: стороны, договорённости, "
        "поручения, открытые вопросы — без повестки и обсуждения. Пустой раздел в "
        "документ не попадает. Строки — простой текст, разметку не писать. "
        "Если источник — расшифровка записи, сначала прочитать её целиком "
        "инструментом transcript_read (все части). "
        "Стиль: тезисы, а не изложение — пункт одна мысль в одну-две строки, без "
        "вводных «клиент сказал»; очевидное не объяснять; без оценочных пояснений; "
        "ни слова о расшифровке и её качестве; без внутреннего — номеров задач, "
        "путей, ставок и денег (деньги — только если клиент просил их зафиксировать); "
        "сотрудники клиента — по имени, только если владелец их назвал, иначе по "
        "роли. Поручение без ответственного — не поручение, а открытый вопрос. "
        "Неясное (кто ответственный, чья учётная запись, какая цифра) не "
        "домысливать: перед вызовом спросить владельца списком; без ответа — пункт "
        "в открытые вопросы или вон. Дату разговора — со слов владельца, по дате "
        "файла не угадывать."
    )

    Input: ClassVar[type[BaseModel]] = ProtocolMakeInput

    def __init__(self, maker: IProtocolMaker) -> None:
        self._maker = maker

    def execute(self, input: ProtocolMakeInput, context: ToolContext) -> str:  # noqa: A002
        return self._maker.make(input).model_dump_json()
