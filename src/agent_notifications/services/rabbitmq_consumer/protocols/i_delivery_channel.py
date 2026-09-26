from typing import Protocol


class IDeliveryChannel(Protocol):
    def basic_ack(self, delivery_tag: int) -> None: ...

    def basic_reject(self, delivery_tag: int, requeue: bool) -> None: ...
