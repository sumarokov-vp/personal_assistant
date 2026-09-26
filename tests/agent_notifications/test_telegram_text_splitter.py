from src.agent_notifications.services.text_splitter import TelegramTextSplitter


def test_short_text_is_one_chunk() -> None:
    assert TelegramTextSplitter(limit=10).split("короткий") == ["короткий"]


def test_prefers_line_break_then_space_then_hard_cut() -> None:
    splitter = TelegramTextSplitter(limit=10)

    assert splitter.split("abc\ndef ghij") == ["abc\n", "def ghij"]
    assert splitter.split("abcd efghijk") == ["abcd ", "efghijk"]
    assert splitter.split("abcdefghijklmno") == ["abcdefghij", "klmno"]


def test_counts_astral_characters_as_two_telegram_units() -> None:
    chunks = TelegramTextSplitter(limit=4).split("😀😀😀")

    assert chunks == ["😀😀", "😀"]
