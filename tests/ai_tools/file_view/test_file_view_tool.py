import io
import json
from pathlib import Path

from ai_framework import Attachment, ToolContext
from PIL import Image

from src.ai_tools.file_view import FileViewTool
from src.ai_tools.file_view.tool import FileViewInput
from src.files.imaging import FileImageRenderer, ImageFitter, PdfRasterizer
from src.files.work_folder.work_folder import WorkFolder

CONTEXT = ToolContext({"chat_id": 1, "user_id": 7})


def tool(work_folder: WorkFolder) -> FileViewTool:
    return FileViewTool(
        work_files=work_folder,
        renderer=FileImageRenderer(
            fitter=ImageFitter(5 * 1024 * 1024), rasterizer=PdfRasterizer(150)
        ),
    )


def scan_pdf(pages: int) -> bytes:
    sheets = [Image.new("RGB", (620, 877), "white") for _ in range(pages)]
    buffer = io.BytesIO()
    sheets[0].save(buffer, format="PDF", save_all=True, append_images=sheets[1:])
    return buffer.getvalue()


def test_pdf_scan_comes_back_as_caption_and_page_images(tmp_path: Path) -> None:
    work_folder = WorkFolder(tmp_path)
    work_file = work_folder.put(scan_pdf(3), "scan.pdf", "application/pdf", "chat")

    output = tool(work_folder).execute(FileViewInput(file_id=work_file.id), CONTEXT)

    assert isinstance(output, list)
    assert isinstance(output[0], str)
    assert "Страниц в документе: 3" in output[0]
    images = [part for part in output if isinstance(part, Attachment)]
    assert [image.media_type for image in images] == ["image/png"] * 3
    assert all(image.to_mcp_content()["type"] == "image" for image in images)


def test_docx_answers_with_error_pointing_to_file_read(tmp_path: Path) -> None:
    work_folder = WorkFolder(tmp_path)
    work_file = work_folder.put(
        b"PK\x03\x04",
        "contract.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "mail",
    )

    output = tool(work_folder).execute(FileViewInput(file_id=work_file.id), CONTEXT)

    assert isinstance(output, str)
    assert "file_read" in json.loads(output)["error"]


def test_unknown_file_id_is_an_error(tmp_path: Path) -> None:
    output = tool(WorkFolder(tmp_path)).execute(
        FileViewInput(file_id="deadbeef"), CONTEXT
    )

    assert isinstance(output, str)
    assert "error" in json.loads(output)
