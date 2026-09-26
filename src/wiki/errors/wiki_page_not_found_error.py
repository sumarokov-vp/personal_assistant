from src.wiki.errors.wiki_error import WikiError


class WikiPageNotFoundError(WikiError):
    def __init__(self, path: str) -> None:
        super().__init__(f"Страницы «{path}» в вики нет")
        self.path = path
