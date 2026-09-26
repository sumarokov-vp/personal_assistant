from typing import Literal, Protocol


class IRenderedImage(Protocol):
    @property
    def media_type(
        self,
    ) -> Literal["image/png", "image/jpeg", "image/gif", "image/webp"]: ...

    @property
    def data(self) -> bytes: ...

    @property
    def reduced(self) -> bool: ...

    @property
    def page(self) -> int | None: ...
