BYTES_IN_MB = 1024 * 1024


class SourceFileTooLargeError(ValueError):
    def __init__(self, name: str, limit: int) -> None:
        super().__init__(
            f"«{name}» больше {limit // BYTES_IN_MB} МБ — в рабочую папку не беру"
        )
        self.name = name
        self.limit = limit
