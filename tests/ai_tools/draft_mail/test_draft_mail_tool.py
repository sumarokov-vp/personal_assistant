import json
from email import message_from_bytes, policy
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import httpx
from ai_framework import ToolContext

from src.ai_tools.draft_mail import DraftAttachments, DraftMailTool
from src.ai_tools.draft_mail.tool import DraftMailInput
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.files.overflow.overflow_folder import OVERFLOW_FOLDER_NAME, OverflowFolder
from src.files.work_folder.work_file import WorkFile
from src.files.work_folder.work_folder import WorkFolder
from tests.gmail.fixtures import PDF_BYTES
from tests.gmail.test_gmail_client import make_client

UPLOAD = "/upload/gmail/v1/users/me/drafts"
DRAFTS = "/gmail/v1/users/me/drafts"
CREATED_DRAFT = {"id": "r-900", "message": {"id": "19e01", "threadId": "19e01"}}
OVER_GMAIL_LIMIT = b"\x00" * (30 * 1024 * 1024)


def build_tool(
    tmp_path: Path, requests: list[httpx.Request], with_dropbox: bool = True
) -> tuple[DraftMailTool, WorkFolder]:
    work_folder = WorkFolder(tmp_path / "work")
    dropbox_root = tmp_path / "Dropbox"
    dropbox_root.mkdir()
    overflow = (
        OverflowFolder(
            DropboxBoundary(root=dropbox_root, policy=DropboxAccessPolicy()),
            work_folder,
        )
        if with_dropbox
        else None
    )
    tool = DraftMailTool(
        drafter=make_client({UPLOAD: CREATED_DRAFT, DRAFTS: CREATED_DRAFT}, requests),
        attachments=DraftAttachments(work_files=work_folder, overflow=overflow),
    )
    return tool, work_folder


def draft_mail(tool: DraftMailTool, *files: WorkFile) -> str:
    return tool.execute(
        DraftMailInput(
            to="Иван Петров <ivan@example.com>",
            subject="Паспорт",
            body="Иван, паспорт во вложении.",
            file_ids=[work_file.id for work_file in files],
        ),
        ToolContext(),
    )


def uploaded_parts(request: httpx.Request) -> tuple[dict[str, Any], EmailMessage]:
    assert request.url.path == UPLOAD
    assert request.url.params["uploadType"] == "multipart"
    envelope = message_from_bytes(
        f"Content-Type: {request.headers['Content-Type']}\r\n\r\n".encode()
        + request.content,
        policy=policy.default,
    )
    assert isinstance(envelope, EmailMessage)
    assert envelope.get_content_type() == "multipart/related"
    metadata_part, mail_part = envelope.iter_parts()
    assert mail_part.get_content_type() == "message/rfc822"
    [mail] = mail_part.iter_parts()
    assert isinstance(mail, EmailMessage)
    return json.loads(metadata_part.get_content()), mail


def test_pdf_goes_to_upload_endpoint_as_attachment(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []
    tool, work_folder = build_tool(tmp_path, requests)
    ticket = work_folder.put(PDF_BYTES, "Билет AirAsia.pdf", "application/pdf", "mail")

    output = draft_mail(tool, ticket)

    [request] = requests
    metadata, mail = uploaded_parts(request)
    [attachment] = list(mail.iter_attachments())
    assert metadata == {"message": {}}
    assert str(mail["To"]) == "Иван Петров <ivan@example.com>"
    assert mail["Subject"] == "Паспорт"
    assert attachment.get_filename() == "Билет AirAsia.pdf"
    assert attachment.get_content_type() == "application/pdf"
    assert attachment.get_content() == PDF_BYTES
    assert "r-900" in output
    assert "не отправлен" in output
    assert "«Билет AirAsia.pdf»" in output


def test_file_over_gmail_limit_goes_to_overflow_folder(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []
    tool, work_folder = build_tool(tmp_path, requests)
    ticket = work_folder.put(PDF_BYTES, "ticket.pdf", "application/pdf", "mail")
    scan = work_folder.put(OVER_GMAIL_LIMIT, "scan.pdf", "application/pdf", "dropbox")

    output = draft_mail(tool, ticket, scan)

    [request] = requests
    _, mail = uploaded_parts(request)
    assert [part.get_filename() for part in mail.iter_attachments()] == ["ticket.pdf"]
    placed = tmp_path / "Dropbox" / OVERFLOW_FOLDER_NAME / "scan.pdf"
    assert placed.read_bytes() == OVER_GMAIL_LIMIT
    assert f"{OVERFLOW_FOLDER_NAME}/scan.pdf" in output
    assert "«scan.pdf» (30.0 МБ) не приложен" in output


def test_without_dropbox_oversized_file_is_named_but_not_saved(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []
    tool, work_folder = build_tool(tmp_path, requests, with_dropbox=False)
    scan = work_folder.put(OVER_GMAIL_LIMIT, "scan.pdf", "application/pdf", "dropbox")

    output = draft_mail(tool, scan)

    [request] = requests
    assert request.url.path == DRAFTS
    assert "«scan.pdf» (30.0 МБ) не приложен" in output
    assert "Dropbox не подключён" in output


def test_unknown_file_id_is_error_without_draft(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []
    tool, _ = build_tool(tmp_path, requests)

    output = tool.execute(
        DraftMailInput(
            to="a@example.com", subject="s", body="b", file_ids=["deadbeef"]
        ),
        ToolContext(),
    )

    assert "error" in json.loads(output)
    assert requests == []
