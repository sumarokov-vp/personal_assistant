from collections.abc import Sequence
from typing import Protocol

from src.ai_tools.colleague_mail.colleagues.protocols.i_colleague import IColleague


class IColleagueDirectory(Protocol):
    def colleagues(self) -> Sequence[IColleague]: ...
