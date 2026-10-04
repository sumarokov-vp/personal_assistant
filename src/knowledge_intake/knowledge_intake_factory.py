from pathlib import Path
from zoneinfo import ZoneInfo

from src.knowledge_intake.models.toolkit_settings import ToolkitSettings
from src.knowledge_intake.repos.allowlist_file import AllowlistFile
from src.knowledge_intake.repos.git_cli import GitCli
from src.knowledge_intake.repos.knowledge_base import KnowledgeBase
from src.knowledge_intake.services.dkim_verifier.dkim_verifier import (
    DkimVerifier,
    TxtLookup,
)
from src.knowledge_intake.services.intake_run.intake_run import IntakeRun
from src.knowledge_intake.services.intake_run.protocols.i_mailbox import IMailbox
from src.knowledge_intake.services.knowledge_distiller.knowledge_distiller import (
    KnowledgeDistiller,
)
from src.knowledge_intake.services.knowledge_distiller.protocols.i_knowledge_model import (
    IKnowledgeModel,
)
from src.knowledge_intake.services.knowledge_distiller.residual_data_check import (
    ResidualDataCheck,
)
from src.knowledge_intake.services.knowledge_distiller.untrusted_letter_frame import (
    UntrustedLetterFrame,
)
from src.knowledge_intake.services.knowledge_publisher.knowledge_publisher import (
    KnowledgePublisher,
)
from src.knowledge_intake.services.letter_reader.html_text import HtmlText
from src.knowledge_intake.services.letter_reader.letter_reader import LetterReader
from src.knowledge_intake.services.sender_gate.sender_gate import SenderGate


class KnowledgeIntakeFactory:
    def __init__(
        self,
        toolkit: ToolkitSettings,
        allowlist_path: Path,
        timezone: ZoneInfo,
        txt_lookup: TxtLookup | None = None,
    ) -> None:
        self._toolkit = toolkit
        self._allowlist_path = allowlist_path
        self._timezone = timezone
        self._txt_lookup = txt_lookup

    def create_run(self, mailbox: IMailbox, model: IKnowledgeModel) -> IntakeRun:
        base = KnowledgeBase(self._toolkit.clone_dir)
        return IntakeRun(
            mailbox=mailbox,
            gate=SenderGate(
                allowlist=AllowlistFile(self._allowlist_path),
                dkim=DkimVerifier(self._txt_lookup),
            ),
            reader=LetterReader(HtmlText()),
            distiller=KnowledgeDistiller(
                model=model,
                index=base,
                plugins=self._toolkit.plugins,
                frame=UntrustedLetterFrame(),
                residual_check=ResidualDataCheck(),
            ),
            publisher=KnowledgePublisher(
                git=GitCli(self._toolkit.clone_dir, self._toolkit.ssh_key_path),
                files=base,
                clone_dir=self._toolkit.clone_dir,
                remote_url=self._toolkit.remote_url,
                branch=self._toolkit.branch,
                author_name=self._toolkit.author_name,
                author_email=self._toolkit.author_email,
                timezone=self._timezone,
            ),
        )
