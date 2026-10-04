import re

CYRILLIC_TO_LATIN = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
    "ә": "a",
    "ғ": "g",
    "қ": "k",
    "ң": "n",
    "ө": "o",
    "ұ": "u",
    "ү": "u",
    "һ": "h",
    "і": "i",
}
MAX_SLUG_LENGTH = 60
FALLBACK_SLUG = "topic"


def topic_slug(topic: str) -> str:
    latin = "".join(CYRILLIC_TO_LATIN.get(char, char) for char in topic.lower())
    slug = re.sub(r"[^a-z0-9]+", "-", latin).strip("-")[:MAX_SLUG_LENGTH].strip("-")
    return slug or FALLBACK_SLUG
