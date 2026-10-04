from dataclasses import dataclass

INDEX_SEPARATOR = " · "


@dataclass(frozen=True)
class IndexLine:
    topic: str
    file: str
    when_to_apply: str

    def render(self) -> str:
        return "- " + INDEX_SEPARATOR.join((self.topic, self.file, self.when_to_apply))
