class InMemoryWikiStorage:
    def __init__(self, files: dict[str, str] | None = None) -> None:
        self.files = dict(files or {})
        self.commits: list[tuple[str, str]] = []

    def read(self, path: str) -> str | None:
        return self.files.get(path)

    def write(self, path: str, content: str, commit_message: str) -> None:
        self.files[path] = content
        self.commits.append((path, commit_message))
