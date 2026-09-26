from typing import Protocol

from src.memory.repos.protocols.i_wiki_page_content import IWikiPageContent


class IWikiPageReader(Protocol):
    def read_page(self, relative_path: str) -> IWikiPageContent: ...
