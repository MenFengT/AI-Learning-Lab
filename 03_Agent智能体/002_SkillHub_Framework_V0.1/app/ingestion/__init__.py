"""File Ingestion Layer公共契约。"""

from .errors import (
    FileIngestionError,
    FileIngestionValidationError,
)
from .models import FileIngestionRequest, FileIngestionResult, IngestionSource
from .protocols import FileIngestionServiceProtocol
from .service import FileIngestionService

__all__ = [
    "FileIngestionError",
    "FileIngestionRequest",
    "FileIngestionResult",
    "FileIngestionService",
    "FileIngestionServiceProtocol",
    "FileIngestionValidationError",
    "IngestionSource",
]
