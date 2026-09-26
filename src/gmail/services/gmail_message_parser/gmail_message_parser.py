import base64
import encodings
import html
from email.message import Message
from typing import Any

from src.gmail.models.mail_message import MailMessage
from src.gmail.models.mail_summary import MailSummary
from src.gmail.models.reply_target import ReplyTarget
from src.gmail.services.gmail_message_parser.html_to_text_converter import (
    HtmlToTextConverter,
)


class GmailMessageParser:
    def __init__(self, html_converter: HtmlToTextConverter) -> None:
        self._html_converter = html_converter

    def parse_summary(self, raw_message: dict[str, Any]) -> MailSummary:
        headers = _headers(raw_message.get("payload", {}))
        return MailSummary(
            id=raw_message["id"],
            thread_id=raw_message["threadId"],
            sender=headers.get("from", ""),
            subject=headers.get("subject", ""),
            date=headers.get("date", ""),
            snippet=html.unescape(raw_message.get("snippet", "")),
        )

    def parse_message(self, raw_message: dict[str, Any]) -> MailMessage:
        payload = raw_message.get("payload", {})
        headers = _headers(payload)
        parts = list(_walk_parts(payload))
        return MailMessage(
            id=raw_message["id"],
            thread_id=raw_message["threadId"],
            sender=headers.get("from", ""),
            recipients=headers.get("to", ""),
            subject=headers.get("subject", ""),
            date=headers.get("date", ""),
            body=self._body_text(parts),
            attachment_names=[
                part["filename"] for part in parts if part.get("filename")
            ],
        )

    def parse_reply_target(self, raw_message: dict[str, Any]) -> ReplyTarget:
        headers = _headers(raw_message.get("payload", {}))
        return ReplyTarget(
            thread_id=raw_message["threadId"],
            recipient=headers.get("reply-to") or headers.get("from", ""),
            subject=headers.get("subject", ""),
            message_id_header=headers.get("message-id", ""),
            references=headers.get("references", ""),
        )

    def _body_text(self, parts: list[dict[str, Any]]) -> str:
        inline_parts = [part for part in parts if not part.get("filename")]
        plain = _first_text_of_type(inline_parts, "text/plain")
        if plain.strip():
            return plain.strip()
        return self._html_converter.convert(
            _first_text_of_type(inline_parts, "text/html")
        )


def _headers(part: dict[str, Any]) -> dict[str, str]:
    return {
        header["name"].lower(): header["value"] for header in part.get("headers", [])
    }


def _walk_parts(part: dict[str, Any]) -> list[dict[str, Any]]:
    found = [part]
    for child in part.get("parts", []):
        found.extend(_walk_parts(child))
    return found


def _first_text_of_type(parts: list[dict[str, Any]], mime_type: str) -> str:
    for part in parts:
        data = part.get("body", {}).get("data")
        if part.get("mimeType", "").lower() == mime_type and data:
            return _decode(data, _charset(part))
    return ""


def _charset(part: dict[str, Any]) -> str:
    header = Message()
    header["Content-Type"] = _headers(part).get("content-type", "text/plain")
    return header.get_content_charset() or "utf-8"


def _decode(data: str, charset: str) -> str:
    raw = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
    return raw.decode(_known_charset(charset), errors="replace")


def _known_charset(charset: str) -> str:
    return charset if encodings.search_function(charset.lower()) else "utf-8"
