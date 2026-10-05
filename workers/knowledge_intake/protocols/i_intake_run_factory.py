from typing import Protocol

from src.knowledge_intake import IKnowledgeModel
from src.knowledge_intake.services.intake_run.protocols.i_mailbox import IMailbox
from workers.knowledge_intake.protocols.i_intake_run import IIntakeRun


class IIntakeRunFactory(Protocol):
    def create_run(self, mailbox: IMailbox, model: IKnowledgeModel) -> IIntakeRun: ...
