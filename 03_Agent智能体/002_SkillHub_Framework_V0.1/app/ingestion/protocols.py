"""File Ingestion Service协议。"""

from typing import Protocol, runtime_checkable

from .models import FileIngestionRequest, FileIngestionResult


@runtime_checkable
class FileIngestionServiceProtocol(Protocol):
    def ingest(self, request: FileIngestionRequest) -> FileIngestionResult: ...
