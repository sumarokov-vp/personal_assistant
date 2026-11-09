import asyncio
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.protocols.services.typst_compiler.typst_compile_error import (
    TypstCompileError,
)

DEFAULT_TIMEOUT_SECONDS = 60
SOURCE_NAME = "document.typ"
PDF_NAME = "document.pdf"
STDERR_MAX_CHARS = 2000


class TypstCompiler:
    def __init__(
        self,
        executable: str = "typst",
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._executable = executable
        self._timeout_seconds = timeout_seconds

    def compile_pdf(self, source: str) -> bytes:
        with tempfile.TemporaryDirectory(prefix="typst-") as workdir:
            source_path = Path(workdir) / SOURCE_NAME
            pdf_path = Path(workdir) / PDF_NAME
            source_path.write_text(source, encoding="utf-8")
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(
                    asyncio.run, self._compile(source_path, pdf_path)
                ).result()
            return pdf_path.read_bytes()

    async def _compile(self, source_path: Path, pdf_path: Path) -> None:
        process = await asyncio.create_subprocess_exec(
            self._executable,
            "compile",
            str(source_path),
            str(pdf_path),
            cwd=source_path.parent,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self._timeout_seconds
            )
        finally:
            if process.returncode is None:
                process.kill()
        if process.returncode != 0:
            message = stderr.decode("utf-8", errors="replace").strip()
            raise TypstCompileError(
                f"Документ не собрался (код {process.returncode}): "
                f"{message[:STDERR_MAX_CHARS]}"
            )
