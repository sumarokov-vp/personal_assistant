from src.wiki.errors.wiki_error import WikiError


class WikiPageEncodingError(WikiError):
    def __init__(self, relative_path: str) -> None:
        super().__init__(
            f"Страница {relative_path} сохранена не в UTF-8: дописать в неё нельзя, "
            "не испортив её байты. Владельцу нужно пересохранить её в UTF-8"
        )
