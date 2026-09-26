from typing import Annotated

from pydantic import AfterValidator


def _collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def _require_text(text: str) -> str:
    if not text:
        raise ValueError("пустое значение")
    return text


CellText = Annotated[str, AfterValidator(_collapse_whitespace)]
RequiredCellText = Annotated[
    str, AfterValidator(_collapse_whitespace), AfterValidator(_require_text)
]
