import base64
import json
import secrets
from collections.abc import Sequence
from typing import Any
from urllib.parse import quote

import httpx

from src.gmail.errors.gmail_attachment_not_found_error import (
    GmailAttachmentNotFoundError,
)
from src.gmail.errors.gmail_attachment_too_large_error import (
    GmailAttachmentTooLargeError,
)
from src.gmail.models.composed_mail import ComposedMail
from src.gmail.models.mail_draft import MailDraft
from src.gmail.models.mail_message import MailMessage
from src.gmail.models.mail_summary import MailSummary
from src.gmail.repos.protocols.i_access_token_provider import IAccessTokenProvider
from src.gmail.repos.protocols.i_gmail_message_parser import IGmailMessageParser
from src.gmail.repos.protocols.i_outgoing_attachment import IOutgoingAttachment
from src.gmail.repos.protocols.i_reply_mime_composer import IReplyMimeComposer

GMAIL_API_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
GMAIL_UPLOAD_URL = "https://gmail.googleapis.com/upload/gmail/v1/users/me"
SUMMARY_HEADERS = ("From", "Subject", "Date")
REPLY_HEADERS = ("From", "Reply-To", "Subject", "Message-ID", "References")
GMAIL_DRAFT_URL = "https://mail.google.com/mail/#drafts?compose={message_id}"
ATTACHMENT_LIMIT_BYTES = 50 * 1024 * 1024


class GmailClient:
    def __init__(
        self,
        http: httpx.Client,
        token_provider: IAccessTokenProvider,
        parser: IGmailMessageParser,
        composer: IReplyMimeComposer,
        api_url: str = GMAIL_API_URL,
        upload_url: str = GMAIL_UPLOAD_URL,
        attachment_limit_bytes: int = ATTACHMENT_LIMIT_BYTES,
    ) -> None:
        self._http = http
        self._token_provider = token_provider
        self._parser = parser
        self._composer = composer
        self._api_url = api_url.rstrip("/")
        self._upload_url = upload_url.rstrip("/")
        self._attachment_limit_bytes = attachment_limit_bytes

    def search_messages(self, query: str, limit: int) -> list[MailSummary]:
        listing = self._request(
            "GET", "/messages", params={"q": query, "maxResults": limit}
        )
        return [
            self._parser.parse_summary(
                self._request(
                    "GET",
                    f"/messages/{quote(item['id'], safe='')}",
                    params={
                        "format": "metadata",
                        "metadataHeaders": list(SUMMARY_HEADERS),
                    },
                )
            )
            for item in listing.get("messages", [])[:limit]
        ]

    def get_message(self, message_id: str) -> MailMessage:
        raw_message = self._request(
            "GET", f"/messages/{quote(message_id, safe='')}", params={"format": "full"}
        )
        return self._parser.parse_message(raw_message)

    def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
        message_path = f"/messages/{quote(message_id, safe='')}"
        source = self._parser.parse_attachment_source(
            self._request("GET", message_path, params={"format": "full"}),
            attachment_id,
        )
        if source is None:
            raise GmailAttachmentNotFoundError(message_id, attachment_id)
        if source.attachment.size > self._attachment_limit_bytes:
            raise GmailAttachmentTooLargeError(
                source.attachment.filename,
                source.attachment.size,
                self._attachment_limit_bytes,
            )
        if source.inline_bytes is not None:
            return source.inline_bytes
        if source.gmail_attachment_id is None:
            return b""
        return self._parser.parse_attachment_bytes(
            self._request(
                "GET",
                f"{message_path}/attachments/"
                f"{quote(source.gmail_attachment_id, safe='')}",
            )
        )

    def create_reply_draft(
        self,
        message_id: str,
        body: str,
        attachments: Sequence[IOutgoingAttachment] = (),
    ) -> MailDraft:
        target = self._parser.parse_reply_target(
            self._request(
                "GET",
                f"/messages/{quote(message_id, safe='')}",
                params={"format": "metadata", "metadataHeaders": list(REPLY_HEADERS)},
            )
        )
        composed = self._composer.compose_reply(target, body, attachments)
        draft = self._post_draft({"threadId": target.thread_id}, composed)
        return self._created_draft(
            draft,
            thread_id=draft["message"].get("threadId", target.thread_id),
            recipient=target.recipient,
            subject=self._composer.reply_subject(target.subject),
            composed=composed,
        )

    def create_draft(
        self,
        recipient: str,
        subject: str,
        body: str,
        attachments: Sequence[IOutgoingAttachment],
    ) -> MailDraft:
        composed = self._composer.compose_new(recipient, subject, body, attachments)
        draft = self._post_draft({}, composed)
        return self._created_draft(
            draft,
            thread_id=draft["message"].get("threadId", ""),
            recipient=recipient,
            subject=subject,
            composed=composed,
        )

    def _post_draft(
        self, message: dict[str, str], composed: ComposedMail
    ) -> dict[str, Any]:
        if not composed.attached:
            raw = base64.urlsafe_b64encode(composed.content).decode()
            return self._request(
                "POST", "/drafts", json={"message": {**message, "raw": raw}}
            )
        return self._upload_draft({"message": message}, composed.content)

    def _upload_draft(
        self, metadata: dict[str, Any], mime_message: bytes
    ) -> dict[str, Any]:
        boundary = _free_boundary(mime_message)
        response = self._http.post(
            f"{self._upload_url}/drafts",
            params={"uploadType": "multipart"},
            content=b"".join(
                (
                    f"--{boundary}\r\n".encode(),
                    b"Content-Type: application/json; charset=UTF-8\r\n\r\n",
                    json.dumps(metadata).encode(),
                    f"\r\n--{boundary}\r\n".encode(),
                    b"Content-Type: message/rfc822\r\n\r\n",
                    mime_message,
                    f"\r\n--{boundary}--\r\n".encode(),
                )
            ),
            headers={
                **self._authorization(),
                "Content-Type": f'multipart/related; boundary="{boundary}"',
            },
        )
        response.raise_for_status()
        return response.json()

    def _created_draft(
        self,
        draft: dict[str, Any],
        thread_id: str,
        recipient: str,
        subject: str,
        composed: ComposedMail,
    ) -> MailDraft:
        draft_message_id = draft["message"]["id"]
        return MailDraft(
            id=draft["id"],
            message_id=draft_message_id,
            thread_id=thread_id,
            recipient=recipient,
            subject=subject,
            url=GMAIL_DRAFT_URL.format(message_id=quote(draft_message_id, safe="")),
            attached=composed.attached,
            left_out=composed.left_out,
        )

    def _authorization(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token_provider.access_token()}"}

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._http.request(
            method,
            f"{self._api_url}{path}",
            params=params,
            json=json,
            headers=self._authorization(),
        )
        response.raise_for_status()
        return response.json()


def _free_boundary(content: bytes) -> str:
    boundary = f"pa-draft-{secrets.token_hex(16)}"
    while boundary.encode() in content:
        boundary = f"pa-draft-{secrets.token_hex(16)}"
    return boundary
