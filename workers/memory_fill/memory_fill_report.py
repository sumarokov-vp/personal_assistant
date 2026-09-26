from dataclasses import dataclass

from workers.memory_fill.page_changes import PageChanges

SUMMARY_LIMIT = 3000


@dataclass(frozen=True)
class MemoryFillReport:
    pages: list[PageChanges]
    model_summary: str

    @property
    def has_changes(self) -> bool:
        return any(page.added or page.updated for page in self.pages)

    def render(self) -> str:
        lines = ["Наполнение памяти завершено."]
        lines.extend(
            f"{page.title}: добавлено {page.added}, обновлено {page.updated}"
            for page in self.pages
        )
        summary = self.model_summary.strip()
        if summary:
            if len(summary) > SUMMARY_LIMIT:
                summary = summary[:SUMMARY_LIMIT].rstrip() + "…"
            lines.extend(["", summary])
        return "\n".join(lines)
