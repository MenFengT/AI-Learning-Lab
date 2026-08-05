"""File Ingestion Layer不可变数据契约。"""

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from app.gateway.models import Attachment
from app.runtime.invocation_context import InvocationContext
from app.services.filesystem.models import FileReference

from .errors import (
    INGESTION_CHECKSUM_MISMATCH,
    INGESTION_REQUEST_INVALID,
    INGESTION_TASK_MISMATCH,
    FileIngestionValidationError,
)


class IngestionSource(str, Enum):
    TELEGRAM = "TELEGRAM"
    WEB = "WEB"
    WECHAT_WORK = "WECHAT_WORK"
    LOCAL_UPLOAD = "LOCAL_UPLOAD"


@dataclass(frozen=True)
class FileIngestionRequest:
    task_id: str
    attachment: Attachment
    runtime_context: InvocationContext
    source: IngestionSource = IngestionSource.LOCAL_UPLOAD
    timeout: float = 10.0

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise FileIngestionValidationError(
                INGESTION_TASK_MISMATCH, "task_id不能为空"
            )
        if self.task_id != self.runtime_context.task_id:
            raise FileIngestionValidationError(
                INGESTION_TASK_MISMATCH,
                "task_id必须与Runtime Context一致",
            )
        if not isinstance(self.attachment, Attachment):
            raise FileIngestionValidationError(
                INGESTION_REQUEST_INVALID, "attachment必须为Attachment"
            )
        if not isinstance(self.source, IngestionSource):
            raise FileIngestionValidationError(
                INGESTION_REQUEST_INVALID, "source无效"
            )
        if self.timeout <= 0:
            raise FileIngestionValidationError(
                INGESTION_REQUEST_INVALID, "timeout必须大于0"
            )


@dataclass(frozen=True)
class FileIngestionResult:
    file_reference: FileReference
    checksum: str
    size: int
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        if not isinstance(self.file_reference, FileReference):
            raise FileIngestionValidationError(
                INGESTION_CHECKSUM_MISMATCH,
                "file_reference必须为FileReference",
            )
        if self.checksum != self.file_reference.checksum:
            raise FileIngestionValidationError(
                INGESTION_CHECKSUM_MISMATCH,
                "result checksum与FileReference不一致",
            )
        if self.size != self.file_reference.metadata.size or self.size < 0:
            raise FileIngestionValidationError(
                INGESTION_CHECKSUM_MISMATCH,
                "result size与FileReference不一致",
            )
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(deepcopy(dict(self.metadata))),
        )
