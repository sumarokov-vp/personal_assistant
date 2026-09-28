from whatsapp_web.documents.errors.document_fetch_error import DocumentFetchError


class DocumentNotFoundError(DocumentFetchError):
    code = "document_not_found"

    def __init__(self) -> None:
        super().__init__("Во вкладке «Документы» чата нет документа с таким именем.")
