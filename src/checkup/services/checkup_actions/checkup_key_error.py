from src.checkup.models.checkup_key import KEY_FORMAT


class CheckupKeyError(ValueError):
    def __init__(self, raw_key: str) -> None:
        super().__init__(
            f"ключ «{raw_key}» не в формате «{KEY_FORMAT}»: "
            "три части через |, срок — дата записи реестра"
        )
        self.raw_key = raw_key
