from src.knowledge_intake.errors.knowledge_intake_error import KnowledgeIntakeError


class IntakeGitError(KnowledgeIntakeError):
    def __init__(self, command: str, details: str) -> None:
        super().__init__(f"git {command}: {details}")
        self.command = command
        self.details = details
