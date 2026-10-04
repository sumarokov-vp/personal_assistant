from src.knowledge_intake.errors.knowledge_intake_error import KnowledgeIntakeError


class ImapCommandError(KnowledgeIntakeError):
    def __init__(self, command: str, status: str) -> None:
        super().__init__(f"IMAP {command}: {status}")
        self.command = command
        self.status = status
