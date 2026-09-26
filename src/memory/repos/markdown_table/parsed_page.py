from dataclasses import dataclass, field


@dataclass
class ParsedPage[T]:
    has_table: bool
    prefix: list[str] = field(default_factory=list)
    entries: list[T] = field(default_factory=list)
    foreign_rows: list[str] = field(default_factory=list)
    suffix: list[str] = field(default_factory=list)
    remarks: list[str] = field(default_factory=list)
