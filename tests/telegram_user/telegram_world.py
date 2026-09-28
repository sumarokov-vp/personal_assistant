from datetime import UTC, datetime

from telethon.tl.types import (
    Channel,
    Chat,
    ChatPhotoEmpty,
    Document,
    DocumentAttributeFilename,
    MessageMediaDocument,
    MessageMediaPhoto,
    Photo,
    PhotoSize,
    PhotoSizeProgressive,
    PhotoStrippedSize,
    User,
)

from tests.telegram_user.fake_telethon_client import FakeTelethonClient

OWNER_ID = 1000
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
CONTRACT_BYTES = b"%PDF-1.7 synthetic contract"
PHOTO_BYTES = b"\xff\xd8\xff synthetic photo"
CONTRACT_SIZE = 123456
PHOTO_LARGEST_SIZE = 150000


def moment(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, day, hour, minute, tzinfo=UTC)


class TelegramWorld:
    def __init__(self) -> None:
        self.client = FakeTelethonClient(OWNER_ID)
        c = self.client
        self.owner = User(
            id=OWNER_ID, is_self=True, first_name="Владелец", access_hash=1
        )
        self.anna = User(
            id=2001, first_name="Анна", last_name="Тестовая", access_hash=11
        )
        self.boris = User(
            id=2002, first_name="Борис", username="boris_test", access_hash=12
        )
        self.dacha = Chat(
            id=3001,
            title="Дача Тест",
            photo=ChatPhotoEmpty(),
            participants_count=3,
            date=CREATED,
            version=1,
        )
        self.site = Channel(
            id=4001,
            title="Стройка Тест",
            photo=ChatPhotoEmpty(),
            date=CREATED,
            megagroup=True,
            access_hash=41,
        )
        self.club = Channel(
            id=4002,
            title="Клуб Тест",
            photo=ChatPhotoEmpty(),
            date=CREATED,
            megagroup=True,
            username="club_test",
            access_hash=42,
        )
        self.news = Channel(
            id=4003,
            title="Новости Тест",
            photo=ChatPhotoEmpty(),
            date=CREATED,
            broadcast=True,
            access_hash=43,
        )
        c.add_entity(self.boris)
        c.add_chat(self.owner, moment(2, 8))
        c.add_chat(self.anna, moment(1, 10))
        c.add_chat(self.dacha, moment(3, 12))
        c.add_chat(self.site, moment(4, 9))
        c.add_chat(self.club, moment(5, 9))
        c.add_chat(self.news, moment(6, 9))

        self.anna_hello = c.add_message(
            self.anna, 1, moment(1, 9), "Привет, договор в пятницу", sender=self.anna
        )
        self.owner_reply = c.add_message(
            self.anna, 2, moment(1, 9, 5), "Ок, жду договор", out=True
        )
        self.anna_contract = c.add_message(
            self.anna,
            3,
            moment(1, 10),
            "Вот договор",
            sender=self.anna,
            media=MessageMediaDocument(document=_contract_document()),
            content=CONTRACT_BYTES,
        )
        self.dacha_photo = c.add_message(
            self.dacha,
            1,
            moment(3, 12),
            "Фото забора",
            sender=self.boris,
            media=MessageMediaPhoto(photo=_fence_photo()),
            content=PHOTO_BYTES,
        )
        self.site_message = c.add_message(
            self.site, 77, moment(4, 9), "Договор подписан", sender=self.anna
        )
        self.club_message = c.add_message(
            self.club, 15, moment(5, 9), "Договор клуба на сезон", sender=self.boris
        )
        self.news_post = c.add_message(self.news, 5, moment(6, 9), "Договор новости")
        self.saved_note = c.add_message(
            self.owner, 9, moment(2, 8), "Заметка себе про договор"
        )


def _contract_document() -> Document:
    return Document(
        id=501,
        access_hash=1,
        file_reference=b"",
        date=moment(1, 10),
        mime_type="application/pdf",
        size=CONTRACT_SIZE,
        dc_id=2,
        attributes=[DocumentAttributeFilename(file_name="Договор.pdf")],
    )


def _fence_photo() -> Photo:
    return Photo(
        id=601,
        access_hash=1,
        file_reference=b"",
        date=moment(3, 12),
        sizes=[
            PhotoStrippedSize(type="i", bytes=b"\x01ab"),
            PhotoSize(type="m", w=320, h=240, size=20000),
            PhotoSizeProgressive(
                type="y", w=1280, h=960, sizes=[10000, 50000, PHOTO_LARGEST_SIZE]
            ),
        ],
        dc_id=2,
    )
