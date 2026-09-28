from collections.abc import Sequence
from typing import Protocol

from src.ai_tools.colleague_mail.colleague_send.protocols.i_colleague import IColleague


class IColleagueDirectory(Protocol):
    def colleagues(self) -> Sequence[IColleague]: ...
