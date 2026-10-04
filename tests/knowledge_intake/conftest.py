import base64
from collections.abc import Callable
from dataclasses import dataclass, field
from email.message import EmailMessage
from pathlib import Path
from uuid import uuid4

import dkim
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from src.knowledge_intake.models.mailbox_folder import MailboxFolder
from src.knowledge_intake.models.raw_letter import RawLetter
from src.knowledge_intake.repos.git_cli import GitCli

SELECTOR = b"intake"
COMPANY_DOMAIN = "company.example"
FOREIGN_DOMAIN = "elsewhere.example"
EMPLOYEE = f"anna@{COMPANY_DOMAIN}"
STRANGER = f"mallory@{COMPANY_DOMAIN}"
FOREIGN_SENDER = f"bob@{FOREIGN_DOMAIN}"
OWNER_IDENTITY = (
    "-c",
    "user.name=Owner",
    "-c",
    "user.email=owner@example.com",
    "-c",
    "commit.gpgsign=false",
)
PLUGIN_JSON = """{
  "name": "mrs-finance",
  "version": "0.3.0",
  "author": { "name": "Test" }
}
"""
SEED_INDEX = (
    "# База знаний mrs-finance\n\n"
    "- Перевыпуск ЭЦП · ecp-reissue.md · перевыпуск ключа ЭЦП юрлица\n"
)
SEED_TOPIC = (
    "---\n"
    "topic: Перевыпуск ЭЦП\n"
    "date: 01.01.2026\n"
    "source: редактор\n"
    "suggested_by: Редактор <editor@company.example>\n"
    "---\n\n"
    "## Суть\n\nЗатравочная запись.\n"
)


@dataclass(frozen=True)
class DkimKeys:
    private_pem: bytes
    public_txt: bytes


def _new_keys() -> DkimKeys:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    public_der = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return DkimKeys(
        private_pem=private_pem,
        public_txt=b"v=DKIM1; k=rsa; p=" + base64.b64encode(public_der),
    )


@pytest.fixture(scope="session")
def company_keys() -> DkimKeys:
    return _new_keys()


@pytest.fixture(scope="session")
def foreign_keys() -> DkimKeys:
    return _new_keys()


@pytest.fixture(scope="session")
def txt_lookup(
    company_keys: DkimKeys, foreign_keys: DkimKeys
) -> Callable[..., bytes | None]:
    records = {
        f"{SELECTOR.decode()}._domainkey.{COMPANY_DOMAIN}": company_keys.public_txt,
        f"{SELECTOR.decode()}._domainkey.{FOREIGN_DOMAIN}": foreign_keys.public_txt,
    }

    def lookup(name: bytes | str, timeout: int = 5) -> bytes | None:
        key = name.decode() if isinstance(name, bytes) else name
        return records.get(key.rstrip("."))

    return lookup


def build_letter(
    sender: str,
    subject: str = "[mrs-knowledge] mrs-finance: справка для банка",
    body: str = "Что делали: перевыпуск ЭЦП.\nТонкости: банк попросил справку.",
    display_name: str = "Анна Тестова",
) -> bytes:
    message = EmailMessage()
    message["From"] = f"{display_name} <{sender}>"
    message["To"] = "knowledge@agent.example"
    message["Subject"] = subject
    message["Message-ID"] = f"<{uuid4().hex}@test.example>"
    message.set_content(body)
    return message.as_bytes()


def sign(raw: bytes, keys: DkimKeys, domain: str) -> bytes:
    signature = dkim.sign(
        raw,
        SELECTOR,
        domain.encode(),
        keys.private_pem,
        include_headers=[b"from", b"to", b"subject", b"message-id"],
    )
    return signature + raw


@dataclass
class FakeMailbox:
    letters: list[RawLetter]
    moves: dict[str, MailboxFolder] = field(default_factory=dict)

    def unread(self) -> list[RawLetter]:
        return [letter for letter in self.letters if letter.uid not in self.moves]

    def move(self, uid: str, folder: MailboxFolder) -> None:
        self.moves[uid] = folder


@dataclass(frozen=True)
class ToolkitRemote:
    bare_dir: Path
    owner_dir: Path

    @property
    def url(self) -> str:
        return str(self.bare_dir)

    def log(self, *args: str) -> str:
        return GitCli(self.bare_dir).run_checked("log", *args, "main")

    def owner_commit(self, relative_path: str, content: str, message: str) -> None:
        owner = GitCli(self.owner_dir)
        owner.run_checked("pull", "--rebase", "origin", "main")
        file = self.owner_dir / relative_path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
        owner.run_checked("add", "--", relative_path)
        owner.run_checked(*OWNER_IDENTITY, "commit", "-m", message)
        owner.run_checked("push", "origin", "HEAD:main")


@pytest.fixture
def toolkit_remote(tmp_path: Path) -> ToolkitRemote:
    bare_dir = tmp_path / "claude-toolkit.git"
    owner_dir = tmp_path / "owner"
    bare_dir.mkdir()
    GitCli(bare_dir).run_checked("init", "--bare", "--initial-branch=main")
    owner_dir.mkdir()
    owner = GitCli(owner_dir)
    owner.run_checked("init", "--initial-branch=main")
    plugin_dir = owner_dir / "plugins" / "mrs-finance"
    (plugin_dir / ".claude-plugin").mkdir(parents=True)
    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        PLUGIN_JSON, encoding="utf-8"
    )
    (plugin_dir / "knowledge").mkdir()
    (plugin_dir / "knowledge" / "INDEX.md").write_text(SEED_INDEX, encoding="utf-8")
    (plugin_dir / "knowledge" / "ecp-reissue.md").write_text(
        SEED_TOPIC, encoding="utf-8"
    )
    owner.run_checked("add", "--all")
    owner.run_checked(*OWNER_IDENTITY, "commit", "-m", "seed")
    owner.run_checked("remote", "add", "origin", str(bare_dir))
    owner.run_checked("push", "origin", "HEAD:main")
    return ToolkitRemote(bare_dir=bare_dir, owner_dir=owner_dir)
