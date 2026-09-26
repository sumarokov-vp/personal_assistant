from typing import Protocol

from src.ai_tools.read_mail.protocols.i_mail_reader import IMailReader
from src.ai_tools.search_mail.protocols.i_mail_searcher import IMailSearcher


class IMailSource(IMailSearcher, IMailReader, Protocol): ...
