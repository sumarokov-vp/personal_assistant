from typing import Protocol

from src.flows.recordings.services.entities.protocol_request import ProtocolRequest


class IProtocolStarter(Protocol):
    def start(self, request: ProtocolRequest) -> None: ...
