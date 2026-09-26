TELEGRAM_MESSAGE_LIMIT = 4096


class TelegramTextSplitter:
    def __init__(self, limit: int = TELEGRAM_MESSAGE_LIMIT) -> None:
        self._limit = limit

    def split(self, text: str) -> list[str]:
        chunks: list[str] = []
        rest = text
        while _telegram_length(rest) > self._limit:
            cut = _break_position(rest, _longest_fitting_prefix(rest, self._limit))
            chunks.append(rest[:cut])
            rest = rest[cut:]
        chunks.append(rest)
        return chunks


def _telegram_length(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def _longest_fitting_prefix(text: str, limit: int) -> int:
    used = 0
    for position, char in enumerate(text):
        used += 2 if ord(char) > 0xFFFF else 1
        if used > limit:
            return position
    return len(text)


def _break_position(text: str, hard_cut: int) -> int:
    for separator in ("\n", " "):
        position = text.rfind(separator, 0, hard_cut)
        if position > 0:
            return position + 1
    return hard_cut
