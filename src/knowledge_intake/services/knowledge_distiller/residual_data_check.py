import re

RESIDUAL_PATTERNS = (
    ("БИН/ИИН", re.compile(r"(?<!\d)\d{12}(?!\d)")),
    (
        "номер счёта IBAN",
        re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", re.IGNORECASE),
    ),
    ("номер карты", re.compile(r"(?<!\d)(?:\d[ -]?){15,18}\d(?!\d)")),
    ("адрес почты", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
)


class ResidualDataCheck:
    def leaked(self, texts: list[str]) -> list[str]:
        joined = "\n".join(texts)
        return [kind for kind, pattern in RESIDUAL_PATTERNS if pattern.search(joined)]
