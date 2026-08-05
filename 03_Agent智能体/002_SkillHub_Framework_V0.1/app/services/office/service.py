"""通过Service Governance访问固定Office MCP Tool。"""

from datetime import datetime
from typing import Any, Mapping

from app.runtime.invocation_context import InvocationContext
from app.runtime.trace import generate_span_id
from app.services.filesystem.models import (
    FileMetadata,
    FileReference,
    WorkspaceArea,
)
from app.services.governance import (
    ServiceCallContext,
    ServiceCallExecutorProtocol,
    ServiceCallPolicy,
)
from app.services.models import MCPRequest, MCPResponse, ServiceResult

from .errors import OFFICE_OPERATION_FAILED, OFFICE_RESPONSE_INVALID
from .models import (
    OfficeDocumentRequest,
    OfficeDocumentResult,
    to_plain,
)


class OfficeService:
    """不调用OfficeCLI、不操作文件，只进行受控Service请求转换。"""

    SERVER_NAME = "office-server"
    TOOLS = {
        "create_document": "office.create_document",
        "update_document": "office.update_document",
        "convert_document": "office.convert_document",
        "export_document": "office.export_document",
    }

    def __init__(
        self,
        governance_executor: ServiceCallExecutorProtocol,
        policies: Mapping[str, ServiceCallPolicy],
    ) -> None:
        missing = set(self.TOOLS) - set(policies)
        if missing:
            raise ValueError(f"Office治理策略缺失：{sorted(missing)}")
        self._governance_executor = governance_executor
        self._policies = dict(policies)

    def create_document(
        self, request: OfficeDocumentRequest
    ) -> ServiceResult[OfficeDocumentResult]:
        return self._execute("create_document", request)

    def update_document(
        self, request: OfficeDocumentRequest
    ) -> ServiceResult[OfficeDocumentResult]:
        return self._execute("update_document", request)

    def convert_document(
        self, request: OfficeDocumentRequest
    ) -> ServiceResult[OfficeDocumentResult]:
        return self._execute("convert_document", request)

    def export_document(
        self, request: OfficeDocumentRequest
    ) -> ServiceResult[OfficeDocumentResult]:
        return self._execute("export_document", request)

    def _execute(
        self, operation: str, request: OfficeDocumentRequest
    ) -> ServiceResult[OfficeDocumentResult]:
        response = self._call(operation, request)
        if not response.success:
            error_code = response.error_code
            if error_code is None or not error_code.startswith("SHF-OFFICE-"):
                error_code = OFFICE_OPERATION_FAILED
            return ServiceResult(
                success=False,
                data=None,
                error_code=error_code,
                message=response.message,
                trace_id=response.trace_id,
                metadata={
                    "span_id": response.span_id,
                    "source_error_code": response.error_code,
                },
            )
        try:
            payload = _mapping(response.content)
            result = OfficeDocumentResult(
                file_reference=_file_reference(_mapping(payload["file"])),
                format=_required_text(payload, "format"),
                metadata=_mapping(payload.get("metadata", {})),
            )
        except (KeyError, TypeError, ValueError):
            return ServiceResult(
                success=False,
                data=None,
                error_code=OFFICE_RESPONSE_INVALID,
                message="Office MCP响应不符合契约",
                trace_id=request.runtime_context.trace_id,
                metadata={"span_id": request.runtime_context.span_id},
            )
        return ServiceResult(
            success=True,
            data=result,
            error_code=None,
            message="Office操作成功",
            trace_id=request.runtime_context.trace_id,
            metadata={"span_id": response.span_id},
        )

    def _call(
        self, operation: str, request: OfficeDocumentRequest
    ) -> MCPResponse:
        context = request.runtime_context
        service_span_id = generate_span_id()
        runtime = InvocationContext(
            task_id=context.task_id,
            trace_id=context.trace_id,
            span_id=service_span_id,
            skill_id=context.skill_id,
            user_id=context.user_id,
            metadata=to_plain(context.metadata),
        )
        arguments = {
            "output_name": request.output_name,
            "content": to_plain(request.content),
            "source_file_id": request.source_file_id,
            "source_version": request.source_version,
            "target_format": request.target_format,
            "idempotency_key": request.idempotency_key,
            "metadata": to_plain(request.metadata),
        }
        tool_name = self.TOOLS[operation]
        return self._governance_executor.execute(
            MCPRequest(
                server_name=self.SERVER_NAME,
                tool_name=tool_name,
                arguments=arguments,
                runtime_context=runtime,
                timeout=request.timeout,
            ),
            ServiceCallContext(
                runtime_context=context,
                service_name="office-service",
                operation_name=operation,
                service_span_id=service_span_id,
                parent_span_id=context.span_id,
                request_metadata={"tool_name": tool_name},
            ),
            self._policies[operation],
        )


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("Office字段必须是对象")
    return value


def _required_text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{key}不能为空")
    return item


def _file_reference(value: Mapping[str, Any]) -> FileReference:
    metadata = _mapping(value["metadata"])
    return FileReference(
        file_id=_required_text(value, "file_id"),
        version=_required_text(value, "version"),
        checksum=_required_text(value, "checksum"),
        area=WorkspaceArea(_required_text(value, "area")),
        relative_path=_required_text(value, "relative_path"),
        metadata=FileMetadata(
            size=int(metadata["size"]),
            content_type=_required_text(metadata, "content_type"),
            created_at=datetime.fromisoformat(_required_text(value, "created_at")),
            updated_at=datetime.fromisoformat(_required_text(value, "updated_at")),
            metadata=_mapping(metadata.get("metadata", {})),
        ),
        created_at=datetime.fromisoformat(_required_text(value, "created_at")),
        updated_at=datetime.fromisoformat(_required_text(value, "updated_at")),
        source_file_id=value.get("source_file_id"),
    )
