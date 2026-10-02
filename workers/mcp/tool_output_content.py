import json

from ai_framework import Attachment
from mcp_types import ContentBlock, ImageContent, TextContent


def to_content_blocks(output: object) -> list[ContentBlock]:
    if isinstance(output, Attachment):
        return [_image(output)]
    if isinstance(output, list) and any(isinstance(item, Attachment) for item in output):
        return [_part(item) for item in output]
    text = (
        output
        if isinstance(output, str)
        else json.dumps(output, ensure_ascii=False, default=str)
    )
    return [TextContent(text=text)]


def _part(item: object) -> ContentBlock:
    if isinstance(item, Attachment):
        return _image(item)
    if isinstance(item, str):
        return TextContent(text=item)
    raise ValueError(
        f"Tool result list mixes attachments with {type(item).__name__}: "
        "only str and Attachment are allowed"
    )


def _image(attachment: Attachment) -> ImageContent:
    content = attachment.to_mcp_content()
    return ImageContent(data=content["data"], mime_type=content["mimeType"])
