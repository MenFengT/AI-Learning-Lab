"""通过FileSystemService解析已上传附件的稳定FileReference。"""

from typing import Any, Mapping

from app.services.filesystem.models import (
    FileOperationRequest,
    FileReference,
    FileSystemRuntimeContext,
)
from app.services.filesystem.protocols import FileSystemServiceProtocol

from .errors import (
    INGESTION_CHECKSUM_MISMATCH,
    INGESTION_FILE_CONFLICT,
    INGESTION_FILE_NOT_FOUND,
    INGESTION_FILESYSTEM_FAILED,
    FileIngestionError,
    FileIngestionValidationError,
)
from .models import FileIngestionRequest, FileIngestionResult


class FileIngestionService:
    """仅查询文件元数据，不读取、写入、移动或修改文件。"""

    def __init__(self, filesystem: FileSystemServiceProtocol) -> None:
        self._filesystem = filesystem

    def ingest(self, request: FileIngestionRequest) -> FileIngestionResult:
        context = request.runtime_context
        result = self._filesystem.list_files(
            FileOperationRequest(
                runtime_context=FileSystemRuntimeContext(
                    task_id=context.task_id,
                    trace_id=context.trace_id,
                    span_id=context.span_id,
                    skill_id=context.skill_id,
                    user_id=context.user_id,
                    metadata=_plain_metadata(context.metadata),
                ),
                source=f"input/{request.attachment.reference_id}",
                timeout=request.timeout,
            )
        )
        if not result.success or result.data is None:
            raise FileIngestionError(
                INGESTION_FILESYSTEM_FAILED,
                "FileSystemService无法查询附件引用",
            )
        candidates = tuple(
            file
            for file in result.data.files
            if _file_name(file) == request.attachment.file_name
        )
        if not candidates:
            raise FileIngestionError(
                INGESTION_FILE_NOT_FOUND,
                "任务输入区不存在匹配附件",
            )
        if len(candidates) != 1:
            raise FileIngestionError(
                INGESTION_FILE_CONFLICT,
                "任务输入区存在多个匹配附件",
            )
        reference = candidates[0]
        if (
            reference.checksum != request.attachment.checksum
            or reference.metadata.size != request.attachment.size
        ):
            raise FileIngestionValidationError(
                INGESTION_CHECKSUM_MISMATCH,
                "附件checksum或size与FileReference不一致",
            )
        return FileIngestionResult(
            file_reference=reference,
            checksum=reference.checksum,
            size=reference.metadata.size,
            metadata={
                "attachment_id": request.attachment.attachment_id,
                "reference_id": request.attachment.reference_id,
                "source": request.source.value,
                "media_type": request.attachment.media_type,
            },
        )


def _file_name(file: FileReference) -> str:
    return file.relative_path.replace("\\", "/").rsplit("/", 1)[-1]


def _plain_metadata(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_metadata(child) for key, child in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(_plain_metadata(child) for child in value)
    return value
