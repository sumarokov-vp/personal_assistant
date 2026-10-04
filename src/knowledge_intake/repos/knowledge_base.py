import json
import re
from datetime import date
from pathlib import Path

from src.knowledge_intake.models.index_line import INDEX_SEPARATOR, IndexLine
from src.knowledge_intake.models.knowledge_entry import KnowledgeEntry
from src.knowledge_intake.models.admitted_sender import AdmittedSender
from src.knowledge_intake.repos.topic_slug import topic_slug

KNOWLEDGE_DIR = "knowledge"
INDEX_FILE = "INDEX.md"
PLUGIN_MANIFEST = Path(".claude-plugin") / "plugin.json"
TOPIC_FILE_PATTERN = re.compile(r"([A-Za-z0-9][A-Za-z0-9._-]*\.md)")
VERSION_PATTERN = re.compile(r'("version"\s*:\s*")(\d+)\.(\d+)\.(\d+)(")')
LIST_MARKERS = "-*+ \t"
TABLE_SEPARATOR = "|"
DATE_FORMAT = "%d.%m.%Y"
FRONT_MATTER = "---"
HEADER_DATE = re.compile(r"^date:.*$", re.MULTILINE)
SECTION_LEVEL = "##"
ADDITION_SECTION_LEVEL = "###"
YAML_UNSAFE = re.compile(r": | #|:$")
YAML_UNSAFE_START = tuple("[]{}&*!|>'\"%@`#,?-")


class KnowledgeBase:
    def __init__(self, clone_dir: Path) -> None:
        self._clone_dir = clone_dir

    def has_plugin(self, plugin: str) -> bool:
        return (self._plugin_dir(plugin) / PLUGIN_MANIFEST).is_file()

    def index_text(self, plugin: str) -> str:
        index = self._index_path(plugin)
        return index.read_text(encoding="utf-8") if index.is_file() else ""

    def index_lines(self, plugin: str) -> list[IndexLine]:
        lines = (
            _parse_index_line(line) for line in self.index_text(plugin).splitlines()
        )
        return [line for line in lines if line is not None]

    def write(
        self,
        entry: KnowledgeEntry,
        sender: AdmittedSender,
        today: date,
    ) -> Path:
        known_files = {line.file for line in self.index_lines(entry.plugin)}
        knowledge_dir = self._plugin_dir(entry.plugin) / KNOWLEDGE_DIR
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        if (
            entry.topic_file in known_files
            and (knowledge_dir / entry.topic_file).is_file()
        ):
            topic_path = knowledge_dir / entry.topic_file
            current = topic_path.read_text(encoding="utf-8")
            topic_path.write_text(
                _with_header_date(current, today) + _addition(entry, sender, today),
                encoding="utf-8",
            )
            return topic_path.relative_to(self._clone_dir)
        topic_path = _free_path(knowledge_dir, topic_slug(entry.topic))
        topic_path.write_text(_new_topic(entry, sender, today), encoding="utf-8")
        self._append_index_line(
            entry.plugin,
            IndexLine(
                topic=_one_line(entry.topic),
                file=topic_path.name,
                when_to_apply=_one_line(entry.when_to_apply),
            ),
        )
        return topic_path.relative_to(self._clone_dir)

    def bump_patch_version(self, plugin: str) -> str:
        manifest = self._plugin_dir(plugin) / PLUGIN_MANIFEST
        text = manifest.read_text(encoding="utf-8")
        match = VERSION_PATTERN.search(text)
        if match is None:
            raise ValueError(f"{manifest}: нет версии x.y.z")
        major, minor, patch = match.group(2), match.group(3), int(match.group(4)) + 1
        version = f"{major}.{minor}.{patch}"
        manifest.write_text(
            VERSION_PATTERN.sub(rf"\g<1>{version}\g<5>", text, count=1),
            encoding="utf-8",
        )
        return version

    def plugin_path(self, plugin: str) -> Path:
        return self._plugin_dir(plugin).relative_to(self._clone_dir)

    def _append_index_line(self, plugin: str, line: IndexLine) -> None:
        index = self._index_path(plugin)
        current = self.index_text(plugin) or f"# База знаний {plugin}\n\n"
        if not current.endswith("\n"):
            current += "\n"
        index.write_text(current + line.render() + "\n", encoding="utf-8")

    def _plugin_dir(self, plugin: str) -> Path:
        return self._clone_dir / "plugins" / plugin

    def _index_path(self, plugin: str) -> Path:
        return self._plugin_dir(plugin) / KNOWLEDGE_DIR / INDEX_FILE


def _parse_index_line(line: str) -> IndexLine | None:
    stripped = line.strip()
    separator = (
        TABLE_SEPARATOR
        if stripped.startswith(TABLE_SEPARATOR)
        else INDEX_SEPARATOR.strip()
    )
    cells = stripped.strip(TABLE_SEPARATOR).lstrip(LIST_MARKERS).split(separator)
    parts = [cell.strip() for cell in cells]
    if len(parts) < 3:
        return None
    file_match = TOPIC_FILE_PATTERN.search(parts[1])
    if file_match is None:
        return None
    return IndexLine(
        topic=parts[0],
        file=file_match.group(1),
        when_to_apply=" · ".join(parts[2:]),
    )


def _free_path(knowledge_dir: Path, slug: str) -> Path:
    candidate = knowledge_dir / f"{slug}.md"
    suffix = 2
    while candidate.exists() or candidate.name == INDEX_FILE:
        candidate = knowledge_dir / f"{slug}-{suffix}.md"
        suffix += 1
    return candidate


def _new_topic(entry: KnowledgeEntry, sender: AdmittedSender, today: date) -> str:
    return (
        "---\n"
        f"topic: {_yaml_scalar(entry.topic)}\n"
        f"date: {_day(today)}\n"
        f"source: {_source(today)}\n"
        f"suggested_by: {_yaml_scalar(sender.signature())}\n"
        "---\n\n"
        f"{_sections(entry, SECTION_LEVEL)}"
    )


def _addition(entry: KnowledgeEntry, sender: AdmittedSender, today: date) -> str:
    return (
        f"\n## Дополнение от {_day(today)}\n\n"
        f"Источник: {_source(today)}; suggested_by: {sender.signature()}\n\n"
        f"{_sections(entry, ADDITION_SECTION_LEVEL)}"
    )


def _with_header_date(text: str, today: date) -> str:
    if not text.startswith(FRONT_MATTER):
        return text if text.endswith("\n") else text + "\n"
    header_end = text.find(f"\n{FRONT_MATTER}", len(FRONT_MATTER))
    if header_end == -1:
        return text
    header = HEADER_DATE.sub(f"date: {_day(today)}", text[:header_end], count=1)
    rest = text[header_end:]
    return header + (rest if rest.endswith("\n") else rest + "\n")


def _sections(entry: KnowledgeEntry, level: str) -> str:
    sections = f"{level} Суть\n\n{entry.essence.strip()}\n"
    if entry.subtleties:
        sections += f"\n{level} Тонкости\n\n" + _bullets(entry.subtleties)
    if entry.sources:
        sections += f"\n{level} Источники и нормы\n\n" + _bullets(entry.sources)
    return sections


def _bullets(items: list[str]) -> str:
    return "".join(f"- {_one_line(item)}\n" for item in items)


def _day(today: date) -> str:
    return today.strftime(DATE_FORMAT)


def _source(today: date) -> str:
    return f"письмо агенту {_day(today)}"


def _yaml_scalar(value: str) -> str:
    line = _one_line(value)
    if YAML_UNSAFE.search(line) or line.startswith(YAML_UNSAFE_START):
        return json.dumps(line, ensure_ascii=False)
    return line


def _one_line(text: str) -> str:
    return " ".join(text.split())
