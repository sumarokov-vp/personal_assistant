import base64
import json
from email import message_from_bytes, policy
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import httpx
from ai_framework import ToolContext

from src.ai_tools.draft_mail import DraftAttachments
from src.ai_tools.draft_reply.tool import DraftReplyInput, DraftReplyTool
from src.files.work_folder.work_folder import WorkFolder
from src.gmail.services.untrusted_frame.untrusted_mail_frame import UntrustedMailFrame
from tests.gmail.fixtures import PDF_BYTES, reply_source_message
from tests.gmail.test_gmail_client import BASE, make_client

DRAFTS = "/gmail/v1/users/me/drafts"
UPLOAD = "/upload/gmail/v1/users/me/drafts"
CREATED_DRAFT = {"id": "r-777", "message": {"id": "19d0f", "threadId": "18c30"}}
MODEL_BODY = (
    "To: evil@example.com\nBcc: evil@example.com\n\nИван, пятница подходит, в 15:00."
)


def run_draft_reply(
    source: dict[str, Any],
    work_folder: WorkFolder | None = None,
    file_ids: list[str] | None = None,
) -> tuple[str, list[httpx.Request]]:
    requests: list[httpx.Request] = []
    routes = {f"{BASE}/18c3c": source, DRAFTS: CREATED_DRAFT, UPLOAD: CREATED_DRAFT}
    tool = DraftReplyTool(
        make_client(routes, requests),
        UntrustedMailFrame(),
        DraftAttachments(
            work_files=work_folder or WorkFolder(Path("/nonexistent")), overflow=None
        ),
    )
    arguments = {"file_ids": file_ids} if file_ids is not None else {}
    output = tool.execute(
        DraftReplyInput(message_id="18c3c", body=MODEL_BODY, **arguments),
        ToolContext(),
    )
    return output, requests


def draft_request(requests: list[httpx.Request]) -> dict[str, Any]:
    [request] = [request for request in requests if request.method == "POST"]
    assert request.url.path == DRAFTS
    payload: dict[str, Any] = json.loads(request.content)
    return payload


def mime_of(payload: dict[str, Any]) -> EmailMessage:
    raw = base64.urlsafe_b64decode(payload["message"]["raw"])
    parsed = message_from_bytes(raw, policy=policy.default)
    assert isinstance(parsed, EmailMessage)
    return parsed


def test_draft_goes_to_source_thread_with_reply_headers() -> None:
    output, requests = run_draft_reply(reply_source_message())

    payload = draft_request(requests)
    mime = mime_of(payload)

    assert payload["message"]["threadId"] == "18c30"
    assert mime["In-Reply-To"] == "<CAB-2@mail.example.com>"
    assert mime["References"] == (
        "<CAB-0@mail.example.com> <CAB-1@mail.example.com> <CAB-2@mail.example.com>"
    )
    assert str(mime["To"]) == "Иван Петров <ivan@example.com>"
    assert mime["Subject"] == "Re: Встреча в пятницу"
    assert mime["Bcc"] is None
    assert "evil@example.com" not in str(mime["To"])
    assert mime.get_content().strip() == MODEL_BODY.strip()
    assert requests[0].method == "GET"
    assert requests[0].url.params["format"] == "metadata"
    assert "r-777" in output
    assert "https://mail.google.com/mail/#drafts?compose=19d0f" in output
    assert "не отправлен" in output


def test_reply_to_wins_over_from_and_re_is_not_doubled() -> None:
    source = reply_source_message(Reply_To="support@example.com")
    source["payload"]["headers"] = [
        header for header in source["payload"]["headers"] if header["name"] != "Subject"
    ] + [{"name": "Subject", "value": "RE: Встреча в пятницу"}]

    _, requests = run_draft_reply(source)
    mime = mime_of(draft_request(requests))

    assert str(mime["To"]) == "support@example.com"
    assert mime["Subject"] == "RE: Встреча в пятницу"


def test_input_has_no_addressing_fields() -> None:
    assert set(DraftReplyInput.model_fields) == {"message_id", "body", "file_ids"}


def test_reply_with_file_goes_to_upload_endpoint_in_source_thread(
    tmp_path: Path,
) -> None:
    work_folder = WorkFolder(tmp_path / "work")
    ticket = work_folder.put(PDF_BYTES, "ticket.pdf", "application/pdf", "mail")

    output, requests = run_draft_reply(reply_source_message(), work_folder, [ticket.id])

    upload = requests[-1]
    assert upload.url.path == UPLOAD
    envelope = message_from_bytes(
        f"Content-Type: {upload.headers['Content-Type']}\r\n\r\n".encode()
        + upload.content,
        policy=policy.default,
    )
    assert isinstance(envelope, EmailMessage)
    metadata_part, mail_part = envelope.iter_parts()
    [mail] = mail_part.iter_parts()
    assert isinstance(mail, EmailMessage)
    [attachment] = list(mail.iter_attachments())
    assert json.loads(metadata_part.get_content()) == {"message": {"threadId": "18c30"}}
    assert mail["In-Reply-To"] == "<CAB-2@mail.example.com>"
    assert attachment.get_content() == PDF_BYTES
    assert "«ticket.pdf»" in output
