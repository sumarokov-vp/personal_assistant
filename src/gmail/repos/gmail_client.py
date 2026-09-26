from typing import Any
from urllib.parse import quote

import httpx

from src.gmail.models.mail_message import MailMessage
from src.gmail.models.mail_summary import MailSummary
from src.gmail.repos.protocols.i_access_token_provider import IAccessTokenProvider
from src.gmail.repos.protocols.i_gmail_message_parser import IGmailMessageParser

GMAIL_API_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
SUMMARY_HEADERS = ("From", "Subject", "Date")


class GmailClient:
    def __init__(
        self,
        http: httpx.Client,
        token_provider: IAccessTokenProvider,
        parser: IGmailMessageParser,
        api_url: str = GMAIL_API_URL,
    ) -> None:
        self._http = http
        self._token_provider = token_provider
        self._parser = parser
        self._api_url = api_url.rstrip("/")

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
            headers={"Authorization": f"Bearer {self._token_provider.access_token()}"},
        )
        response.raise_for_status()
        return response.json()
