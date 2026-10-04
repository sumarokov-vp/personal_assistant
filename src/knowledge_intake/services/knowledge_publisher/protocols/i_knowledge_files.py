from datetime import date
from pathlib import Path
from typing import Protocol

from src.knowledge_intake.models.admitted_sender import AdmittedSender
from src.knowledge_intake.models.knowledge_entry import KnowledgeEntry


class IKnowledgeFiles(Protocol):
    def write(
        self,
        entry: KnowledgeEntry,
        sender: AdmittedSender,
        today: date,
    ) -> Path: ...

    def bump_patch_version(self, plugin: str) -> str: ...

    def plugin_path(self, plugin: str) -> Path: ...
