from datetime import datetime, time, timedelta


def next_digest_at(now: datetime, at: time) -> datetime:
    today = datetime.combine(now.date(), at, tzinfo=now.tzinfo)
    return today if today > now else today + timedelta(days=1)
