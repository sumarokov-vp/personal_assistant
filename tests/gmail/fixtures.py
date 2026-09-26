import base64
from typing import Any


def encode(text: str, charset: str = "utf-8") -> str:
    return base64.urlsafe_b64encode(text.encode(charset)).decode().rstrip("=")


def headers(**values: str) -> list[dict[str, str]]:
    return [
        {"name": name.replace("_", "-").title(), "value": value}
        for name, value in values.items()
    ]


def multipart_message() -> dict[str, Any]:
    return {
        "id": "18c1a",
        "threadId": "18c00",
        "snippet": "Привет, это &quot;тест&quot;",
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": headers(
                From="Банк <bank@example.com>",
                To="me@example.com",
                Subject="Выписка",
                Date="Sat, 26 Sep 2026 10:00:00 +0500",
            ),
            "body": {"size": 0},
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "headers": [],
                    "body": {"size": 0},
                    "parts": [
                        {
                            "mimeType": "text/plain",
                            "headers": headers(
                                Content_Type='text/plain; charset="UTF-8"'
                            ),
                            "body": {
                                "data": encode("Выписка за сентябрь во вложении.\n")
                            },
                        },
                        {
                            "mimeType": "text/html",
                            "headers": headers(Content_Type="text/html; charset=UTF-8"),
                            "body": {"data": encode("<p>HTML-версия</p>")},
                        },
                    ],
                },
                {
                    "mimeType": "application/pdf",
                    "filename": "statement.pdf",
                    "headers": headers(Content_Type="application/pdf"),
                    "body": {"attachmentId": "att1", "size": 1024},
                },
            ],
        },
    }


def html_only_message() -> dict[str, Any]:
    html = (
        "<html><head><style>p {color: red}</style><title>t</title></head><body>"
        "<script>alert(1)</script><p>Здравствуйте,&nbsp;Владимир!</p>"
        "<div>Счёт&nbsp;№&nbsp;42 &amp; акт</div><br><ul><li>первое</li><li>второе</li></ul>"
        "</body></html>"
    )
    return {
        "id": "18c2b",
        "threadId": "18c2b",
        "snippet": "Здравствуйте",
        "payload": {
            "mimeType": "text/html",
            "headers": headers(
                From="shop@example.com",
                To="me@example.com",
                Subject="Счёт",
                Date="Fri, 25 Sep 2026",
                Content_Type="text/html; charset=windows-1251",
            ),
            "body": {"data": encode(html, "windows-1251")},
        },
    }


def reply_source_message(**extra_headers: str) -> dict[str, Any]:
    return {
        "id": "18c3c",
        "threadId": "18c30",
        "snippet": "Когда встречаемся?",
        "payload": {
            "mimeType": "text/plain",
            "headers": headers(
                From="Иван Петров <ivan@example.com>",
                Subject="Встреча в пятницу",
                Message_Id="<CAB-2@mail.example.com>",
                References="<CAB-0@mail.example.com> <CAB-1@mail.example.com>",
                **extra_headers,
            ),
        },
    }
