from typing import Protocol


class IPdfRasterizer(Protocol):
    def page_count(self, content: bytes) -> int: ...

    def render_png(self, content: bytes, page_numbers: list[int]) -> list[bytes]: ...
