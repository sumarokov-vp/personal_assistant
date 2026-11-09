from src.protocols.models.protocol_content import ProtocolContent
from src.protocols.services.protocol_maker.protocol_document import (
    PDF_SUFFIX,
    TYP_SUFFIX,
    ProtocolDocument,
)
from src.protocols.services.protocol_maker.protocol_file_stem import protocol_file_stem
from src.protocols.services.protocol_maker.protocol_files import ProtocolFiles
from src.protocols.services.protocol_maker.protocols.i_pdf_compiler import IPdfCompiler
from src.protocols.services.protocol_maker.protocols.i_protocol_source import (
    IProtocolSource,
)
from src.protocols.services.protocol_maker.protocols.i_protocol_storage import (
    IProtocolStorage,
)


class ProtocolMaker:
    def __init__(
        self,
        source: IProtocolSource,
        compiler: IPdfCompiler,
        storage: IProtocolStorage,
    ) -> None:
        self._source = source
        self._compiler = compiler
        self._storage = storage

    def make(self, content: ProtocolContent) -> ProtocolFiles:
        return self.store(self.compose(content))

    def compose(self, content: ProtocolContent) -> ProtocolDocument:
        typst_source = self._source.render(content)
        return ProtocolDocument(
            file_stem=protocol_file_stem(
                content.iso_date, self._source.document_title(content), content.title
            ),
            typst_source=typst_source,
            pdf=self._compiler.compile_pdf(typst_source),
        )

    def store(self, document: ProtocolDocument) -> ProtocolFiles:
        typ_path = self._storage.write_new_file(
            f"{self._storage.folder}/{document.typ_name}",
            document.typst_source.encode("utf-8"),
        )
        pdf_path = self._storage.write_new_file(
            typ_path.removesuffix(TYP_SUFFIX) + PDF_SUFFIX, document.pdf
        )
        return ProtocolFiles(pdf_path=pdf_path, typ_path=typ_path)
