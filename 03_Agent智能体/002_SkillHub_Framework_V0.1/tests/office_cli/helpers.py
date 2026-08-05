from datetime import datetime, timezone

from app.mcp_servers.office.runtime import OfficeCLIResult
from app.services.filesystem.models import FileMetadata, FileReference, WorkspaceArea


class RecordingAudit:
    def __init__(self) -> None:
        self.events = []

    def record(self, event) -> None:
        self.events.append(event)


class FakeOfficeRuntime:
    def __init__(self) -> None:
        self.calls = []

    def _call(self, request):
        self.calls.append(request)
        return OfficeCLIResult(file_reference=file_reference(), format="docx")

    create_document = _call
    update_document = _call
    convert_document = _call
    export_document = _call


def file_reference() -> FileReference:
    now = datetime.now(timezone.utc)
    return FileReference(
        file_id="file-office-cli-001",
        version="1",
        checksum="a" * 64,
        area=WorkspaceArea.OUTPUT,
        relative_path="output/task-001/result.docx",
        metadata=FileMetadata(
            size=128,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            created_at=now,
            updated_at=now,
        ),
        created_at=now,
        updated_at=now,
    )


def context() -> dict[str, str]:
    return {
        "task_id": "task-001",
        "trace_id": "trace-001",
        "span_id": "span-001",
        "skill_id": "local/document_automation@0.3.0",
    }
