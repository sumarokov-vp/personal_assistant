from src.protocols.models.protocol_kind import ProtocolKind

DOCUMENT_TITLES = {
    ProtocolKind.MEETING: "Протокол встречи",
    ProtocolKind.CALL: "Протокол звонка",
}
PARTIES_TITLES = {
    ProtocolKind.MEETING: "Участники",
    ProtocolKind.CALL: "Стороны",
}
AGREEMENTS_TITLES = {
    ProtocolKind.MEETING: "Решения",
    ProtocolKind.CALL: "Договорённости",
}
AGENDA_TITLE = "Повестка"
DISCUSSION_TITLE = "Обсуждение"
ACTIONS_TITLE = "Поручения"
OPEN_QUESTIONS_TITLE = "Открытые вопросы"
