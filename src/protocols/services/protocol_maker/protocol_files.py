from pydantic import BaseModel


class ProtocolFiles(BaseModel):
    pdf_path: str
    typ_path: str
