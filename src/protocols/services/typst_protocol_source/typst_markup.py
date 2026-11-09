import re

MARKUP_CHARS = re.compile(r"([\\#*_@$<>`\[\]/~])")
LINE_START_MARKERS = re.compile(r"^(=|-|\+|\d+\.)")
WHITESPACE = re.compile(r"\s+")


def escaped(text: str) -> str:
    single_line = WHITESPACE.sub(" ", text).strip()
    literal = MARKUP_CHARS.sub(r"\\\1", single_line)
    return LINE_START_MARKERS.sub(r"\\\1", literal)


def heading(title: str, level: int = 1) -> str:
    return f"{'=' * level} {title}"


def bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {escaped(item)}" for item in items)


def numbered_list(items: list[str]) -> str:
    return "\n".join(f"+ {escaped(item)}" for item in items)


def table(header: list[str], rows: list[list[str]]) -> str:
    cells = [
        "  table.header(" + ", ".join(f"[*{title}*]" for title in header) + "),",
        *("  " + ", ".join(f"[{escaped(cell)}]" for cell in row) + "," for row in rows),
    ]
    columns = ", ".join(["auto", "1fr", *["auto"] * (len(header) - 2)])
    return "\n".join(["#table(", f"  columns: ({columns}),", *cells, ")"])
