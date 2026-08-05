from datetime import datetime, timezone

from app.runtime.invocation_context import InvocationContext
from app.services.governance import (
    AuditPolicy,
    CircuitCallPolicy,
    Idempotency,
    OperationType,
    ServiceCallPolicy,
)
from app.services.models import MCPResponse
from app.services.office.models import OfficeDocumentRequest
from app.services.resilience import RetryPolicy


def runtime_context() -> InvocationContext:
    return InvocationContext(
        task_id="task-office-001",
        trace_id="trace-office-001",
        span_id="span-skill-001",
        skill_id="local/document_automation@0.3.0",
    )


def office_request() -> OfficeDocumentRequest:
    return OfficeDocumentRequest(
        runtime_context=runtime_context(),
        output_name="result.docx",
        content={"title": "测试文档", "sections": ()},
        idempotency_key="task-office-001:create",
        timeout=5.0,
    )


def policy() -> ServiceCallPolicy:
    return ServiceCallPolicy(
        operation_type=OperationType.WRITE,
        idempotency=Idempotency.IDEMPOTENT_WITH_KEY,
        retry_policy=RetryPolicy(1, 0, 0, 1, frozenset()),
        circuit_policy=CircuitCallPolicy(),
        audit_policy=AuditPolicy(),
        timeout_budget=5.0,
    )


def policies() -> dict[str, ServiceCallPolicy]:
    return {
        operation: policy()
        for operation in (
            "create_document",
            "update_document",
            "convert_document",
            "export_document",
        )
    }


def file_payload() -> dict[str, object]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "file_id": "file-office-001",
        "version": "1",
        "checksum": "checksum-office-001",
        "area": "output",
        "relative_path": "output/result.docx",
        "created_at": now,
        "updated_at": now,
        "source_file_id": None,
        "metadata": {
            "size": 128,
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "metadata": {},
        },
    }


def mcp_response(*, success: bool = True) -> MCPResponse:
    return MCPResponse(
        success=success,
        content={"file": file_payload(), "format": "docx", "metadata": {}}
        if success
        else None,
        error_code=None if success else "SHF-OFFICE-OPERATION-FAILED",
        message="ok" if success else "failed",
        server_name="office-server",
        tool_name="office.create_document",
        trace_id="trace-office-001",
        span_id="span-service-001",
        duration_ms=1,
        attempts=1,
    )
