from string import hexdigits

INTAKE_ID_HEX_LENGTH = 16


class RecordingCallback:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def data(self, intake_id: str) -> str:
        return f"{self.prefix}{intake_id}"

    def intake_id(self, data: str | None) -> str | None:
        if data is None or not data.startswith(self.prefix):
            return None
        intake_id = data.removeprefix(self.prefix)
        if len(intake_id) != INTAKE_ID_HEX_LENGTH or not all(
            char in hexdigits for char in intake_id
        ):
            return None
        return intake_id
