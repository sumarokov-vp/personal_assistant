from pydantic import BaseModel, ConfigDict


class CdnDownload(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: int
    content: bytes
    oversized: bool
