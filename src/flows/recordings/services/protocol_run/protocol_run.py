from logging import getLogger

from src.flows.recordings.services.entities.protocol_request import ProtocolRequest
from src.flows.recordings.services.protocol_drafter.protocol_draft_error import (
    ProtocolDraftError,
)
from src.flows.recordings.services.protocol_drafter.protocol_model_error import (
    ProtocolModelError,
)
from src.flows.recordings.services.protocol_run.protocol_run_result import (
    ProtocolRunResult,
)
from src.flows.recordings.services.protocol_run.protocol_run_text import (
    ProtocolRunText,
)
from src.flows.recordings.services.protocol_run.protocols.i_protocol_chat import (
    IProtocolChat,
)
from src.flows.recordings.services.protocol_run.protocols.i_protocol_documents import (
    IProtocolDocuments,
)
from src.flows.recordings.services.protocol_run.protocols.i_protocol_drafter import (
    IProtocolDrafter,
)
from src.flows.recordings.services.protocol_run.protocols.i_protocol_text_messages import (
    IProtocolTextMessages,
)
from src.flows.recordings.services.protocol_run.protocols.i_transcript_loader import (
    ITranscriptLoader,
)
from src.flows.recordings.services.transcript_source.transcript_missing_error import (
    TranscriptMissingError,
)
from src.protocols.models.protocol_content import ProtocolContent
from src.protocols.services.typst_compiler.typst_compile_error import (
    TypstCompileError,
)

TIMEOUT_REASON = "модель не ответила вовремя, попробуйте ещё раз позже"

logger = getLogger(__name__)


class ProtocolRun:
    def __init__(
        self,
        transcripts: ITranscriptLoader,
        drafter: IProtocolDrafter,
        documents: IProtocolDocuments,
        text_messages: IProtocolTextMessages,
        chat: IProtocolChat,
        text: ProtocolRunText,
    ) -> None:
        self._transcripts = transcripts
        self._drafter = drafter
        self._documents = documents
        self._text_messages = text_messages
        self._chat = chat
        self._text = text

    def run(self, request: ProtocolRequest) -> ProtocolRunResult:
        result = ProtocolRunResult(
            progress_message_id=self._chat.send_html(
                request.chat_id, self._text.progress(request.kind)
            )
        )
        content = self._content(request, result)
        if content is None:
            return result
        result.text_message_ids = [
            self._chat.send_html(request.chat_id, message)
            for message in self._text_messages.messages(content)
        ]
        self._send_pdf(request, content, result)
        return result

    def _content(
        self, request: ProtocolRequest, result: ProtocolRunResult
    ) -> ProtocolContent | None:
        try:
            transcript = self._transcripts.load(request)
            return self._drafter.draft(request.kind, transcript)
        except (
            TranscriptMissingError,
            ProtocolDraftError,
            ProtocolModelError,
        ) as error:
            self._fail(request, result, str(error))
        except TimeoutError:
            self._fail(request, result, TIMEOUT_REASON)
        return None

    def _send_pdf(
        self,
        request: ProtocolRequest,
        content: ProtocolContent,
        result: ProtocolRunResult,
    ) -> None:
        try:
            document = self._documents.compose(content)
        except TypstCompileError as error:
            logger.warning("Protocol: typst failed: %s", error)
            result.failure = str(error)
            self._chat.send_html(request.chat_id, self._text.pdf_failed(str(error)))
            return
        try:
            result.files = self._documents.store(document)
        except OSError as error:
            logger.warning("Protocol: archive failed: %s", error)
            result.archive_error = str(error)
        result.pdf_message_id = self._chat.send_pdf(
            request.chat_id,
            document.pdf_name,
            document.pdf,
            self._text.pdf_caption(result.files.pdf_path if result.files else None),
        )
        if result.archive_error is not None:
            self._chat.send_html(
                request.chat_id, self._text.archive_failed(result.archive_error)
            )

    def _fail(
        self, request: ProtocolRequest, result: ProtocolRunResult, reason: str
    ) -> None:
        logger.warning("Protocol %s failed: %s", request.transcript_id, reason)
        result.failure = reason
        self._chat.send_html(request.chat_id, self._text.failed(request.kind, reason))
