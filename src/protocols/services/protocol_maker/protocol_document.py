from pydantic import BaseModel, ConfigDict

TYP_SUFFIX = ".typ"
PDF_SUFFIX = ".pdf"


class ProtocolDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_stem: str
    typst_source: str
    pdf: bytes

    @property
    def pdf_name(self) -> str:
        return f"{self.file_stem}{PDF_SUFFIX}"

    @property
    def typ_name(self) -> str:
        return f"{self.file_stem}{TYP_SUFFIX}"
