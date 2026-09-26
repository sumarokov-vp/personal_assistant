from typing import Protocol

from src.ai_tools.file_view.protocols.i_rendered_images import IRenderedImages


class IFileImageRenderer(Protocol):
    def render(
        self, content: bytes, media_type: str, name: str, pages: list[int] | None
    ) -> IRenderedImages: ...
