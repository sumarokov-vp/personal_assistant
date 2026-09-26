from src.wiki.errors.wiki_error import WikiError


class WikiGitError(WikiError):
    def __init__(self, command: str, details: str) -> None:
        super().__init__(f"git {command}: {details}")
        self.command = command
        self.details = details
