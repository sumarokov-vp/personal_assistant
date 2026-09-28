class DocumentFetchError(Exception):
    code = "fetch_failed"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail
