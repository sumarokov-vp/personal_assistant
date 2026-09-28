from datetime import datetime, time
from zoneinfo import ZoneInfo

from src.colleague_mail.services.digest import next_digest_at

ALMATY = ZoneInfo("Asia/Almaty")
NINE = time(9, 0)


def test_before_term_waits_for_today() -> None:
    now = datetime(2026, 9, 28, 8, 59, tzinfo=ALMATY)

    assert next_digest_at(now, NINE) == datetime(2026, 9, 28, 9, 0, tzinfo=ALMATY)


def test_restart_after_term_waits_for_tomorrow() -> None:
    now = datetime(2026, 9, 28, 9, 0, tzinfo=ALMATY)

    assert next_digest_at(now, NINE) == datetime(2026, 9, 29, 9, 0, tzinfo=ALMATY)
