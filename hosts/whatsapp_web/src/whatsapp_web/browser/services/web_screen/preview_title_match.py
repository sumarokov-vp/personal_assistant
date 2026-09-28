class PreviewTitleMatch:
    def __init__(self, prefix: str) -> None:
        self._prefix = prefix

    def indexes(self, titles: list[str], file_name: str) -> list[int]:
        names = [self._shown_name(title) for title in titles]
        exact = [index for index, name in enumerate(names) if name == file_name]
        if exact:
            return exact
        with_extension = file_name + "."
        return [
            index
            for index, name in enumerate(names)
            if name is not None
            and name.startswith(with_extension)
            and "." not in name.removeprefix(with_extension)
        ]

    def _shown_name(self, title: str) -> str | None:
        if not title.startswith(self._prefix) or not title.endswith('"'):
            return None
        return title.removeprefix(self._prefix).removesuffix('"')
