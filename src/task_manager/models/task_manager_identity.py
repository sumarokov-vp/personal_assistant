from pydantic import BaseModel, Field

REF_SEPARATOR = ":"


class TaskManagerIdentity(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    title: str

    def ref(self, native_id: str) -> str:
        return f"{self.key}{REF_SEPARATOR}{native_id}"

    def owns(self, ref: str | None) -> bool:
        return self.native_id(ref) is not None

    def native_id(self, ref: str | None) -> str | None:
        prefix = f"{self.key}{REF_SEPARATOR}"
        if ref is None or not ref.startswith(prefix):
            return None
        return ref.removeprefix(prefix) or None
