from typing import Protocol


class IPdfCompiler(Protocol):
    def compile_pdf(self, source: str) -> bytes: ...
