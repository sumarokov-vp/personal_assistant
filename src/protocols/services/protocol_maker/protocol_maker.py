from src.protocols.models.protocol_content import ProtocolContent
from src.protocols.services.protocol_maker.protocol_file_stem import protocol_file_stem
from src.protocols.services.protocol_maker.protocol_files import ProtocolFiles
from src.protocols.services.protocol_maker.protocols.i_pdf_compiler import IPdfCompiler
from src.protocols.services.protocol_maker.protocols.i_protocol_source import (
    IProtocolSource,
)
from src.protocols.services.protocol_maker.protocols.i_protocol_storage import (
    IProtocolStorage,
)

TYP_SUFFIX = ".typ"
PDF_SUFFIX = ".pdf"


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
        typst_source = self._source.render(content)
        pdf = self._compiler.compile_pdf(typst_source)
        stem = protocol_file_stem(
            content.iso_date, self._source.document_title(content), content.title
        )
        typ_path = self._storage.write_new_file(
            f"{self._storage.folder}/{stem}{TYP_SUFFIX}", typst_source.encode("utf-8")
        )
        pdf_path = self._storage.write_new_file(
            typ_path.removesuffix(TYP_SUFFIX) + PDF_SUFFIX, pdf
        )
        return ProtocolFiles(pdf_path=pdf_path, typ_path=typ_path)
