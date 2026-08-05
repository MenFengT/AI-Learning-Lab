"""FileSystem Service：只进行权限、逻辑路径、MCP转换和审计。"""

from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping, TypeVar

from app.runtime.invocation_context import InvocationContext
from app.runtime.trace import generate_span_id
from app.services.audit import AuditEvent, AuditServiceProtocol
from app.services.governance import (
    Idempotency,
    OperationType,
    ServiceCallContext,
    ServiceCallExecutorProtocol,
    ServiceCallPolicy,
)
from app.services.models import MCPRequest, MCPResponse, ServiceResult

from .errors import DELETE_CONFIRM_REQUIRED, MCP_UNAVAILABLE, PERMISSION_DENIED
from .models import (
    DeleteConfirmation,
    DeleteRequest,
    FileMetadata,
    FileOperationRequest,
    FileOperationResult,
    FileReference,
    FileSystemRuntimeContext,
    WorkspaceArea,
)
from .permissions import FilePermission, FileSystemAccessPolicy, WorkspacePolicy


T = TypeVar("T")


class FileSystemService:
    """Skill侧文件基础设施入口；不直接访问文件系统。"""

    SERVER_NAME = "filesystem-server"
    TOOLS = {
        "list": "filesystem.list",
        "read": "filesystem.read",
        "write": "filesystem.write",
        "copy": "filesystem.copy",
        "move": "filesystem.move",
        "rename": "filesystem.rename",
        "archive": "filesystem.archive",
        "request_delete": "filesystem.request_delete",
        "confirm_delete": "filesystem.confirm_delete",
    }

    def __init__(
        self,
        governance_executor: ServiceCallExecutorProtocol,
        access_policy: FileSystemAccessPolicy,
        workspace_policy: WorkspacePolicy,
        audit_service: AuditServiceProtocol,
        governance_policies: Mapping[str, ServiceCallPolicy],
    ) -> None:
        self._validate_governance_policies(governance_policies)
        self._governance_executor = governance_executor
        self._access_policy = access_policy
        self._workspace_policy = workspace_policy
        self._audit_service = audit_service
        self._governance_policies = MappingProxyType(
            dict(governance_policies)
        )

    def list_files(self, request: FileOperationRequest) -> ServiceResult[FileOperationResult]:
        return self._operation(request, "list", FilePermission.LIST)

    def read_file(self, request: FileOperationRequest) -> ServiceResult[FileOperationResult]:
        return self._operation(request, "read", FilePermission.READ)

    def write_file(self, request: FileOperationRequest) -> ServiceResult[FileOperationResult]:
        return self._operation(request, "write", FilePermission.WRITE)

    def copy_file(self, request: FileOperationRequest) -> ServiceResult[FileOperationResult]:
        return self._operation(request, "copy", FilePermission.COPY)

    def move_file(self, request: FileOperationRequest) -> ServiceResult[FileOperationResult]:
        return self._operation(request, "move", FilePermission.MOVE)

    def rename_file(self, request: FileOperationRequest) -> ServiceResult[FileOperationResult]:
        return self._operation(request, "rename", FilePermission.RENAME)

    def archive_file(self, request: FileOperationRequest) -> ServiceResult[FileOperationResult]:
        return self._operation(request, "archive", FilePermission.ARCHIVE)

    def request_delete(self, request: DeleteRequest) -> ServiceResult[DeleteConfirmation]:
        denied = self._permission_denied(
            request.runtime_context, FilePermission.DELETE, "request_delete"
        )
        if denied is not None:
            return denied
        try:
            path = self._workspace_policy.validate_path(request.path)
            self._workspace_policy.validate_task_id(request.runtime_context.task_id)
        except ValueError as exc:
            return self._local_failure(request.runtime_context, "request_delete", str(exc))
        response = self._call(
            "request_delete",
            {
                "path": path,
                "expected_version": request.expected_version,
                "expected_checksum": request.expected_checksum,
            },
            request.runtime_context,
            request.timeout,
        )
        if not response.success:
            return self._mcp_failure(response, request.runtime_context, "request_delete")
        try:
            value = self._mapping(response.content)
            confirmation = DeleteConfirmation(
                confirmation_id=str(value["confirmation_id"]),
                file_id=str(value["file_id"]),
                version=str(value["version"]),
                checksum=str(value["checksum"]),
                expire_time=datetime.fromisoformat(str(value["expire_time"])),
            )
        except (KeyError, TypeError, ValueError):
            return self._local_failure(
                request.runtime_context, "request_delete", "MCP响应无效"
            )
        return self._success(confirmation, request.runtime_context)

    def confirm_delete(self, request: DeleteRequest) -> ServiceResult[FileOperationResult]:
        denied = self._permission_denied(
            request.runtime_context, FilePermission.DELETE, "confirm_delete"
        )
        if denied is not None:
            return denied
        if not request.confirmation_id:
            return self._local_failure(
                request.runtime_context,
                "confirm_delete",
                "缺少confirmation_id",
                DELETE_CONFIRM_REQUIRED,
            )
        try:
            path = self._workspace_policy.validate_path(request.path)
        except ValueError as exc:
            return self._local_failure(request.runtime_context, "confirm_delete", str(exc))
        response = self._call(
            "confirm_delete",
            {
                "path": path,
                "confirmation_id": request.confirmation_id,
                "expected_version": request.expected_version,
                "expected_checksum": request.expected_checksum,
            },
            request.runtime_context,
            request.timeout,
        )
        return self._operation_response(response, request.runtime_context, "confirm_delete", path, None)

    def _operation(
        self,
        request: FileOperationRequest,
        operation: str,
        permission: FilePermission,
    ) -> ServiceResult[FileOperationResult]:
        denied = self._permission_denied(request.runtime_context, permission, operation)
        if denied is not None:
            return denied
        try:
            self._workspace_policy.validate_task_id(request.runtime_context.task_id)
            source = (
                self._workspace_policy.validate_path(request.source)
                if request.source is not None
                else None
            )
            target = (
                self._workspace_policy.validate_path(request.target)
                if request.target is not None
                else None
            )
            sources = tuple(
                self._workspace_policy.validate_path(item)
                for item in request.sources
            )
        except ValueError as exc:
            return self._local_failure(request.runtime_context, operation, str(exc))
        response = self._call(
            operation,
            {
                "source": source,
                "target": target,
                "content": request.content,
                "sources": sources,
                "expected_version": request.expected_version,
                "overwrite": request.overwrite,
                "archive_action": request.archive_action,
            },
            request.runtime_context,
            request.timeout,
        )
        return self._operation_response(response, request.runtime_context, operation, source, target)

    def _operation_response(
        self,
        response: MCPResponse,
        context: FileSystemRuntimeContext,
        operation: str,
        source: str | None,
        target: str | None,
    ) -> ServiceResult[FileOperationResult]:
        if not response.success:
            return self._mcp_failure(response, context, operation, source, target)
        try:
            value = self._mapping(response.content)
            file_value = value.get("file")
            files_value = value.get("files", [])
            result = FileOperationResult(
                operation=operation,
                file=self._file(self._mapping(file_value)) if file_value else None,
                files=tuple(self._file(self._mapping(item)) for item in files_value),
                content=value.get("content"),
            )
        except (KeyError, TypeError, ValueError):
            return self._local_failure(context, operation, "MCP响应无效")
        file_id = result.file.file_id if result.file else None
        version = result.file.version if result.file else None
        return self._success(result, context)

    def _call(self, operation: str, arguments: Mapping[str, Any], context: FileSystemRuntimeContext, timeout: float) -> MCPResponse:
        service_span_id = generate_span_id()
        service_runtime = InvocationContext(
            task_id=context.task_id,
            trace_id=context.trace_id,
            span_id=service_span_id,
            skill_id=context.skill_id,
            user_id=context.user_id,
            metadata=_to_plain_value(context.metadata),
        )
        request = MCPRequest(
            server_name=self.SERVER_NAME,
            tool_name=self.TOOLS[operation],
            arguments=arguments,
            runtime_context=service_runtime,
            timeout=timeout,
        )
        call_context = ServiceCallContext(
            runtime_context=context,
            service_name="filesystem-service",
            operation_name=operation,
            service_span_id=service_span_id,
            parent_span_id=context.span_id,
            request_metadata={"tool_name": self.TOOLS[operation]},
        )
        return self._governance_executor.execute(
            request,
            call_context,
            self._governance_policies[operation],
        )

    def _permission_denied(self, context: FileSystemRuntimeContext, permission: FilePermission, operation: str) -> ServiceResult[Any] | None:
        if self._access_policy.allows(context.skill_id, permission):
            return None
        self._audit(context, operation, None, None, None, None, "FAILED", PERMISSION_DENIED)
        return ServiceResult(False, None, PERMISSION_DENIED, "Skill无权执行文件操作", context.trace_id, {"span_id": context.span_id})

    def _local_failure(self, context: FileSystemRuntimeContext, operation: str, message: str, error_code: str = "SHF-SVC-FILE-INVALID_PATH") -> ServiceResult[Any]:
        self._audit(context, operation, None, None, None, None, "FAILED", error_code)
        return ServiceResult(False, None, error_code, message, context.trace_id, {"span_id": context.span_id})

    def _mcp_failure(self, response: MCPResponse, context: FileSystemRuntimeContext, operation: str, source: str | None = None, target: str | None = None) -> ServiceResult[Any]:
        error_code = response.error_code or MCP_UNAVAILABLE
        return ServiceResult(False, None, error_code, response.message, response.trace_id, {"span_id": response.span_id})

    @classmethod
    def _validate_governance_policies(
        cls, policies: Mapping[str, ServiceCallPolicy]
    ) -> None:
        expected = {
            "list": (OperationType.READ, Idempotency.IDEMPOTENT),
            "read": (OperationType.READ, Idempotency.IDEMPOTENT),
            "write": (
                OperationType.WRITE,
                Idempotency.IDEMPOTENT_WITH_KEY,
            ),
            "copy": (
                OperationType.WRITE,
                Idempotency.IDEMPOTENT_WITH_KEY,
            ),
            "move": (OperationType.MOVE, Idempotency.NON_IDEMPOTENT),
            "rename": (OperationType.MOVE, Idempotency.NON_IDEMPOTENT),
            "archive": (
                OperationType.ARCHIVE,
                Idempotency.IDEMPOTENT_WITH_KEY,
            ),
            "request_delete": (
                OperationType.DELETE,
                Idempotency.NON_IDEMPOTENT,
            ),
            "confirm_delete": (
                OperationType.DELETE,
                Idempotency.NON_IDEMPOTENT,
            ),
        }
        if set(policies) != set(cls.TOOLS):
            raise ValueError("FileSystem治理策略必须覆盖全部固定操作")
        for operation, (operation_type, idempotency) in expected.items():
            policy = policies[operation]
            if (
                policy.operation_type is not operation_type
                or policy.idempotency is not idempotency
            ):
                raise ValueError(f"FileSystem治理策略不匹配：{operation}")

    @staticmethod
    def _success(data: T, context: FileSystemRuntimeContext) -> ServiceResult[T]:
        return ServiceResult(True, data, None, "文件操作成功", context.trace_id, {"span_id": context.span_id})

    def _audit(self, context: FileSystemRuntimeContext, operation: str, source: str | None, target: str | None, file_id: str | None, version: str | None, result: str, error_code: str | None) -> None:
        self._audit_service.record(
            AuditEvent(
                task_id=context.task_id,
                trace_id=context.trace_id,
                span_id=context.span_id,
                skill_id=context.skill_id,
                server=self.SERVER_NAME,
                tool=self.TOOLS[operation],
                duration=0.0,
                error_code=error_code,
                metadata={"operation": operation, "file_id": file_id, "version": version, "source": source, "target": target, "result": result},
            )
        )

    @staticmethod
    def _mapping(value: Any) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise TypeError("响应必须是对象")
        return value

    @classmethod
    def _file(cls, value: Mapping[str, Any]) -> FileReference:
        metadata_value = cls._mapping(value["metadata"])
        created_at = datetime.fromisoformat(str(value["created_at"]))
        updated_at = datetime.fromisoformat(str(value["updated_at"]))
        metadata = FileMetadata(
            size=int(metadata_value["size"]),
            content_type=str(metadata_value["content_type"]),
            created_at=created_at,
            updated_at=updated_at,
            metadata=cls._mapping(metadata_value.get("metadata", {})),
        )
        return FileReference(
            file_id=str(value["file_id"]), version=str(value["version"]),
            checksum=str(value["checksum"]), area=WorkspaceArea(str(value["area"])),
            relative_path=str(value["relative_path"]), metadata=metadata,
            created_at=created_at, updated_at=updated_at,
            source_file_id=value.get("source_file_id"),
        )


def _to_plain_value(value: Any) -> Any:
    """复制只读Runtime metadata，交由Service span重新冻结。"""
    if isinstance(value, Mapping):
        return {
            str(key): _to_plain_value(child)
            for key, child in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(_to_plain_value(child) for child in value)
    return value
