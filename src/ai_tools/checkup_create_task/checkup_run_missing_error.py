class CheckupRunMissingError(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "checkup_create_task работает только внутри прогона чекапа: "
            "в контексте инструмента нет итога прогона"
        )
