class MemoryPageFormatError(Exception):
    def __init__(self, path: str, remarks: list[str]) -> None:
        super().__init__(f"{path}: {'; '.join(remarks)}")
        self.path = path
        self.remarks = remarks
