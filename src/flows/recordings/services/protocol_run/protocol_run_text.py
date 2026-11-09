from html import escape

from src.protocols.models.protocol_kind import ProtocolKind

KIND_NAMES = {
    ProtocolKind.MEETING: "протокол встречи",
    ProtocolKind.CALL: "протокол звонка",
}


class ProtocolRunText:
    def progress(self, kind: ProtocolKind) -> str:
        return f"Составляю {KIND_NAMES[kind]}…"

    def failed(self, kind: ProtocolKind, reason: str) -> str:
        return f"Не получилось составить {KIND_NAMES[kind]}: {escape(reason)}."

    def pdf_failed(self, reason: str) -> str:
        return f"PDF протокола не собрался: {escape(reason)}. Текст протокола — выше."

    def pdf_caption(self, archived_pdf: str | None) -> str:
        if archived_pdf is None:
            return "Протокол в PDF."
        return f"Протокол в PDF. Копия — {escape(archived_pdf)}."

    def archive_failed(self, reason: str) -> str:
        return (
            f"Копию протокола в архив записей не сохранил: {escape(reason)}. "
            "Протокол выше — полный."
        )
