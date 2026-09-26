from src.wiki.errors.wiki_error import WikiError


class WikiPathError(WikiError):
    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Путь «{path}» отклонён: {reason}")
        self.path = path
        self.reason = reason
