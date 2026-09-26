# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Получить refresh token Gmail владельца и положить его в pass.

Запуск (из корня репы personal_assistant, на машине с ключом pass ассистента):

    uv run scripts/gmail_auth.py

OAuth-клиент (Desktop app, JSON client_secret_*.json целиком) берётся из pass
``assistant/personal_assistant/gmail-oauth-client``. Скрипт печатает ссылку согласия
(scope gmail.readonly + gmail.compose, offline, prompt=consent) и ждёт код двумя путями:

- браузер на этой же машине — Google перенаправит на ``http://localhost:<порт>``, код
  примет локальный сервер сам;
- браузер на другой машине — страница localhost не откроется, это нормально: скопируй
  полный адрес из адресной строки и вставь сюда, Enter.

Refresh token уходит в ``pass insert -m`` и на экран не выводится; печатается только
«сохранено» и адрес ящика (users.getProfile) — чтобы проверить, что вошёл нужный аккаунт.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import select
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

CLIENT_PASS_ENTRY = "assistant/personal_assistant/gmail-oauth-client"
TOKEN_PASS_ENTRY = "assistant/personal_assistant/gmail-refresh-token"
SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
)
AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
PROFILE_URI = "https://gmail.googleapis.com/gmail/v1/users/me/profile"


def load_client() -> tuple[str, str]:
    raw = subprocess.run(
        ["pass", "show", CLIENT_PASS_ENTRY],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    data = json.loads(raw)
    section = data.get("installed") or data.get("web")
    if not section:
        sys.exit(f"В {CLIENT_PASS_ENTRY} нет секции installed/web — это не JSON клиента Google")
    return section["client_id"], section["client_secret"]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def parse_redirect(url: str, state: str) -> str:
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url.strip()).query)
    if "error" in query:
        sys.exit(f"Google вернул ошибку: {query['error'][0]}")
    if query.get("state", [None])[0] != state:
        sys.exit("state в адресе не совпал — это адрес не от этой попытки, запусти скрипт заново")
    code = query.get("code", [None])[0]
    if not code:
        sys.exit("В адресе нет code — скопируй адресную строку целиком")
    return code


class _Catcher(http.server.BaseHTTPRequestHandler):
    url: str | None = None
    got = threading.Event()

    def do_GET(self) -> None:  # noqa: N802
        if "code=" not in self.path and "error=" not in self.path:
            self.send_response(404)
            self.end_headers()
            return
        type(self).url = "http://localhost" + self.path
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Готово, вернись в терминал.".encode())
        type(self).got.set()

    def log_message(self, *args: object) -> None:
        return


def wait_redirect(port: int) -> str:
    server = http.server.HTTPServer(("127.0.0.1", port), _Catcher)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        while not _Catcher.got.is_set():
            ready, _, _ = select.select([sys.stdin], [], [], 0.5)
            if ready:
                line = sys.stdin.readline()
                if not line:
                    sys.exit("stdin закрыт, адрес не получен")
                if line.strip():
                    return line.strip()
        assert _Catcher.url is not None
        return _Catcher.url
    finally:
        server.shutdown()


def post_form(url: str, form: dict[str, str]) -> dict:
    request = urllib.request.Request(url, data=urllib.parse.urlencode(form).encode())
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        try:
            detail = json.loads(body)
            body = f"{detail.get('error')}: {detail.get('error_description', '')}"
        except ValueError:
            pass
        sys.exit(f"Обмен кода не удался: {exc.code} {body}")


def fetch_email(access_token: str) -> str:
    request = urllib.request.Request(
        PROFILE_URI, headers={"Authorization": f"Bearer {access_token}"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)["emailAddress"]
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        try:
            body = json.loads(body)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            pass
        return f"не прочитан: Gmail API ответил {exc.code} — {body}"


def store_token(refresh_token: str) -> None:
    subprocess.run(
        ["pass", "insert", "-m", "-f", TOKEN_PASS_ENTRY],
        input=refresh_token + "\n",
        check=True,
        text=True,
        stdout=subprocess.DEVNULL,
    )


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)
    client_id, client_secret = load_client()
    port = free_port()
    redirect_uri = f"http://localhost:{port}"
    state = secrets.token_urlsafe(16)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    auth_url = AUTH_URI + "?" + urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    print("1. Открой ссылку в браузере и разреши доступ:\n")
    print(auth_url)
    print(
        "\n2. Браузер уйдёт на localhost. На этой машине — всё случится само."
        "\n   На другой машине страница не загрузится — скопируй адрес из адресной строки"
        "\n   целиком, вставь сюда и нажми Enter.\n"
    )
    code = parse_redirect(wait_redirect(port), state)
    tokens = post_form(
        TOKEN_URI,
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        },
    )
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        sys.exit("Google не выдал refresh token — отзови доступ на myaccount.google.com/permissions и повтори")
    granted = set(tokens.get("scope", "").split())
    missing = [scope for scope in SCOPES if scope not in granted]
    if missing:
        sys.exit(f"Выданы не все права, не хватает: {', '.join(missing)} — повтори и отметь все галочки")
    store_token(refresh_token)
    print(f"сохранено в pass {TOKEN_PASS_ENTRY}")
    print(f"аккаунт: {fetch_email(tokens['access_token'])}")


if __name__ == "__main__":
    main()
