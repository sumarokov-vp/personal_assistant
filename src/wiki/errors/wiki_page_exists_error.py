from src.wiki.errors.wiki_error import WikiError


class WikiPageExistsError(WikiError):
    def __init__(self, path: str) -> None:
        super().__init__(f"Страница «{path}» уже есть в вики")
        self.path = path
