from pydantic import ValidationError

from src.memory.repos import MemoryPageFormatError
from src.wiki import WikiError

MEMORY_ERRORS = (MemoryPageFormatError, WikiError, ValidationError)
