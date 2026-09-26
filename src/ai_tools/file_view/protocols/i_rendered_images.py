from collections.abc import Sequence
from typing import Protocol

from src.ai_tools.file_view.protocols.i_rendered_image import IRenderedImage


class IRenderedImages(Protocol):
    @property
    def images(self) -> Sequence[IRenderedImage]: ...

    @property
    def page_count(self) -> int | None: ...
