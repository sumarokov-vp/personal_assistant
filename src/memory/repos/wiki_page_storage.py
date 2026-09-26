from src.memory.repos.protocols.i_wiki_page_reader import IWikiPageReader
from src.memory.repos.protocols.i_wiki_page_writer import IWikiPageWriter


class WikiPageStorage:
    def __init__(
        self,
        reader: IWikiPageReader,
        writer: IWikiPageWriter,
        page_not_found_error: type[Exception],
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._page_not_found_error = page_not_found_error

    def read(self, path: str) -> str | None:
        try:
            return self._reader.read_page(path).content
        except self._page_not_found_error:
            return None

    def write(self, path: str, content: str, commit_message: str) -> None:
        self._writer.write_page(path, content, commit_message)
