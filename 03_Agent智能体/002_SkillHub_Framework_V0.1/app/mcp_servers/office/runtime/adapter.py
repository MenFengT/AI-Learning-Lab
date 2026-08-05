"""固定 Office MCP Tool 到外部 OfficeCLI API 的安全适配器。"""

from time import monotonic
from typing import Any, Callable, Mapping

from app.services.audit.models import AuditEvent
from app.services.audit.protocols import AuditServiceProtocol
from app.services.filesystem.models import FileReference

from .errors import (
    OfficeCLIAdapterError,
    OfficeCLIInvocationError,
    OfficeCLIRequestError,
    OfficeCLIResponseError,
)
from .models import OfficeCLIRequest, OfficeCLIResult
from .protocols import OfficeCLIRuntimeProtocol


class OfficeCLIAdapter:
    """不使用Shell；只调用注入的四个固定OfficeCLI Runtime方法。"""

    def __init__(
        self,
        runtime: OfficeCLIRuntimeProtocol,
        audit_service: AuditServiceProtocol,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._runtime = runtime
        self._audit_service = audit_service
        self._clock = clock

    def create_document(self, arguments: Mapping[str, Any], runtime_context: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._invoke("create_document", arguments, runtime_context)

    def update_document(self, arguments: Mapping[str, Any], runtime_context: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._invoke("update_document", arguments, runtime_context)

    def convert_document(self, arguments: Mapping[str, Any], runtime_context: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._invoke("convert_document", arguments, runtime_context)

    def export_document(self, arguments: Mapping[str, Any], runtime_context: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._invoke("export_document", arguments, runtime_context)

    def _invoke(self, operation: str, arguments: Mapping[str, Any], context: Mapping[str, Any]) -> Mapping[str, Any]:
        started = self._clock()
        request = _request(operation, arguments, context)
        self._audit(request, operation, "OFFICE_CLI_STARTED", 0.0, None)
        try:
            handler = getattr(self._runtime, operation)
            result = handler(request)
            if not isinstance(result, OfficeCLIResult):
                raise OfficeCLIResponseError("OfficeCLI返回类型无效")
            response = _result_mapping(result)
        except OfficeCLIAdapterError as exc:
            self._audit(request, operation, "OFFICE_CLI_FAILED", self._clock() - started, exc.error_code)
            raise
        except Exception as exc:
            error = OfficeCLIInvocationError("OfficeCLI外部能力调用失败")
            self._audit(request, operation, "OFFICE_CLI_FAILED", self._clock() - started, error.error_code)
            raise error from exc
        self._audit(request, operation, "OFFICE_CLI_SUCCEEDED", self._clock() - started, None)
        return response

    def _audit(self, request: OfficeCLIRequest, operation: str, event_type: str, duration: float, error_code: str | None) -> None:
        self._audit_service.record(
            AuditEvent(
                task_id=request.task_id,
                trace_id=request.trace_id,
                span_id=request.span_id,
                skill_id=request.skill_id,
                server="office-cli",
                tool=f"office.{operation}",
                duration=max(0.0, duration),
                error_code=error_code,
                metadata={"event_type": event_type},
            )
        )


def _request(operation: str, arguments: Mapping[str, Any], context: Mapping[str, Any]) -> OfficeCLIRequest:
    try:
        return OfficeCLIRequest(
            operation=operation,
            arguments=arguments,
            task_id=str(context["task_id"]),
            trace_id=str(context["trace_id"]),
            span_id=str(context["span_id"]),
            skill_id=str(context["skill_id"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise OfficeCLIRequestError("OfficeCLI请求上下文无效") from exc


def _result_mapping(result: OfficeCLIResult) -> Mapping[str, Any]:
    reference = result.file_reference
    return {
        "file": _file_reference_mapping(reference),
        "format": result.format,
        "metadata": dict(result.metadata),
    }


def _file_reference_mapping(value: FileReference) -> Mapping[str, Any]:
    return {
        "file_id": value.file_id,
        "version": value.version,
        "checksum": value.checksum,
        "area": value.area.value,
        "relative_path": value.relative_path,
        "created_at": value.created_at.isoformat(),
        "updated_at": value.updated_at.isoformat(),
        "source_file_id": value.source_file_id,
        "metadata": {
            "size": value.metadata.size,
            "content_type": value.metadata.content_type,
            "metadata": dict(value.metadata.metadata),
        },
    }
