from datetime import datetime, timezone

from app.gateway import Attachment, AttachmentType
from app.runtime.invocation_context import InvocationContext
from app.services.filesystem.models import (
    FileMetadata,
    FileOperationResult,
    FileReference,
    WorkspaceArea,
)
from app.services.models import ServiceResult


CHECKSUM = "0123456789abcdef"


def attachment(*, checksum: str = CHECKSUM, size: int = 128) -> Attachment:
    return Attachment(
        attachment_id="attachment-001",
        attachment_type=AttachmentType.WORD,
        file_name="input.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size=size,
        checksum=checksum,
        reference_id="upload-001",
    )


def runtime() -> InvocationContext:
    return InvocationContext(
        task_id="task-ingestion-001",
        trace_id="trace-ingestion-001",
        span_id="span-ingestion-001",
        skill_id="local/file_ingestion@0.6.0",
    )


def file_reference(*, checksum: str = CHECKSUM, size: int = 128) -> FileReference:
    now = datetime.now(timezone.utc)
    return FileReference(
        file_id="file-ingestion-001",
        version="1",
        checksum=checksum,
        area=WorkspaceArea.INPUT,
        relative_path="input/upload-001/input.docx",
        metadata=FileMetadata(
            size,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            now,
            now,
        ),
        created_at=now,
        updated_at=now,
    )


class RecordingFileSystem:
    def __init__(self, files=None, *, allowed: bool = True) -> None:
        self.files = tuple(files if files is not None else (file_reference(),))
        self.allowed = allowed
        self.requests: list[object] = []

    def list_files(self, request):
        self.requests.append(request)
        if not self.allowed:
            return ServiceResult(
                False,
                None,
                "SHF-SVC-FILE-PERMISSION_DENIED",
                "permission denied",
                request.runtime_context.trace_id,
            )
        return ServiceResult(
            True,
            FileOperationResult("list", files=self.files),
            None,
            "ok",
            request.runtime_context.trace_id,
        )

    def __getattr__(self, name: str):
        raise AssertionError(f"Ingestion禁止调用FileSystem操作：{name}")
