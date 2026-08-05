"""OfficeCLI Runtime Protocol 到外部OfficeCLI MCP Server的固定桥接。"""

from datetime import datetime
from typing import Any, Mapping

from app.mcp_servers.office.runtime.errors import OfficeCLIInvocationError
from app.mcp_servers.office.runtime.models import OfficeCLIRequest, OfficeCLIResult
from app.services.filesystem.models import FileMetadata, FileReference, WorkspaceArea

from .errors import BridgeConnectionError, BridgeResponseError, BridgeToolError
from .models import OfficeCLIBridgeTool, OfficeCLIMCPCall
from .protocols import TransportProviderProtocol


class OfficeCLIMCPBridgeAdapter:
    """使用固定Tool和受控数据契约连接外部OfficeCLI MCP Server。"""

    _TOOLS = {
        "create_document": OfficeCLIBridgeTool.CREATE_DOCUMENT,
        "update_document": OfficeCLIBridgeTool.UPDATE_DOCUMENT,
        "convert_document": OfficeCLIBridgeTool.CONVERT_DOCUMENT,
        "export_document": OfficeCLIBridgeTool.EXPORT_DOCUMENT,
    }

    def __init__(self, transport_provider: TransportProviderProtocol, *, timeout: float = 30.0) -> None:
        if timeout <= 0:
            raise ValueError("timeout必须大于0")
        self._transport_provider = transport_provider
        self._timeout = timeout

    def create_document(self, request: OfficeCLIRequest) -> OfficeCLIResult:
        return self._invoke("create_document", request)

    def update_document(self, request: OfficeCLIRequest) -> OfficeCLIResult:
        return self._invoke("update_document", request)

    def convert_document(self, request: OfficeCLIRequest) -> OfficeCLIResult:
        return self._invoke("convert_document", request)

    def export_document(self, request: OfficeCLIRequest) -> OfficeCLIResult:
        return self._invoke("export_document", request)

    def _invoke(self, operation: str, request: OfficeCLIRequest) -> OfficeCLIResult:
        if not isinstance(request, OfficeCLIRequest) or request.operation != operation:
            raise OfficeCLIInvocationError("OfficeCLI Bridge请求操作不一致")
        call = OfficeCLIMCPCall(
            self._TOOLS[operation], request.arguments,
            request.task_id, request.trace_id, request.span_id, request.skill_id,
            self._timeout,
        )
        transport = self._transport_provider.create()
        try:
            transport.connect()
            response = transport.call(call)
        except Exception as exc:
            if isinstance(exc, (BridgeToolError, BridgeResponseError)):
                raise
            raise BridgeConnectionError("OfficeCLI MCP Transport调用失败") from exc
        finally:
            transport.close()
        if not response.success:
            raise BridgeToolError(response.message or "OfficeCLI MCP Tool失败", response.error_code or "SHF-OFFICE-BRIDGE-TOOL_FAILED")
        if response.content is None:
            raise BridgeResponseError("OfficeCLI MCP成功响应缺少content")
        return _office_result(response.content)


def _office_result(content: Mapping[str, Any]) -> OfficeCLIResult:
    try:
        file = _mapping(content["file"])
        metadata = _mapping(file["metadata"])
        created_at = datetime.fromisoformat(_text(file, "created_at"))
        updated_at = datetime.fromisoformat(_text(file, "updated_at"))
        reference = FileReference(
            file_id=_text(file, "file_id"), version=_text(file, "version"),
            checksum=_text(file, "checksum"), area=WorkspaceArea(_text(file, "area")),
            relative_path=_text(file, "relative_path"),
            metadata=FileMetadata(
                size=int(metadata["size"]), content_type=_text(metadata, "content_type"),
                created_at=created_at, updated_at=updated_at,
                metadata=_mapping(metadata.get("metadata", {})),
            ),
            created_at=created_at, updated_at=updated_at,
            source_file_id=file.get("source_file_id"),
        )
        return OfficeCLIResult(reference, _text(content, "format"), _mapping(content.get("metadata", {})))
    except (KeyError, TypeError, ValueError) as exc:
        raise BridgeResponseError("OfficeCLI MCP响应不符合FileReference契约") from exc


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("字段必须是Mapping")
    return value


def _text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{key}不能为空")
    return item
