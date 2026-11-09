import re

FORBIDDEN_IN_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')
WHITESPACE = re.compile(r"\s+")
MAX_TITLE_CHARS = 80


def protocol_file_stem(iso_date: str, document_title: str, title: str) -> str:
    clean_title = WHITESPACE.sub(" ", FORBIDDEN_IN_NAME.sub(" ", title)).strip(" .")
    return f"{iso_date} {document_title} — {clean_title[:MAX_TITLE_CHARS].rstrip()}"
