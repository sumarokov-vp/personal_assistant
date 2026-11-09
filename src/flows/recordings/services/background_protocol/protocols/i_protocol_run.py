from typing import Protocol

from src.flows.recordings.services.entities.protocol_request import ProtocolRequest


class IProtocolRun(Protocol):
    def run(self, request: ProtocolRequest) -> object: ...
