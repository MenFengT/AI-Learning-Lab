"""固定Office能力到真实OfficeCLI MCP Transport的Runtime实现。"""

from typing import Any, Mapping

from app.mcp_servers.office.runtime.errors import OfficeCLIInvocationError
from app.mcp_servers.office.runtime.models import OfficeCLIRequest, OfficeCLIResult
from app.mcp_servers.office.runtime.output_resolver import (
    OfficeCLIOutputResolverProtocol,
)

from .capability_mapper import OfficeCLICapabilityMapper
from .mapping_models import (
    OfficeCapability,
    OfficeCapabilityRequest,
    OfficeDocumentContent,
)
from .protocols import TransportProviderProtocol


class MappedOfficeCLIRuntime:
    """只执行Mapper生成的固定调用计划，不接受command或动态Tool。"""

    _CAPABILITIES = {
        "create_document": OfficeCapability.CREATE_DOCUMENT,
        "update_document": OfficeCapability.UPDATE_DOCUMENT,
        "convert_document": OfficeCapability.CONVERT_DOCUMENT,
        "export_document": OfficeCapability.EXPORT_DOCUMENT,
    }

    def __init__(
        self,
        mapper: OfficeCLICapabilityMapper,
        transport_provider: TransportProviderProtocol,
        output_resolver: OfficeCLIOutputResolverProtocol,
    ) -> None:
        self._mapper = mapper
        self._transport_provider = transport_provider
        self._output_resolver = output_resolver

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
            raise OfficeCLIInvocationError("OfficeCLI Runtime请求操作不一致")
        capability_request = OfficeCapabilityRequest(
            capability=self._CAPABILITIES[operation],
            task_id=request.task_id,
            document_name=_required_text(request.arguments, "output_name"),
            content=_document_content(request.arguments),
        )
        plan = self._mapper.map(capability_request)
        self._output_resolver.prepare(request)
        responses = []
        for call in plan.calls:
            transport = self._transport_provider.create()
            try:
                transport.connect()
                response = transport.call(call)
                if not response.success:
                    raise OfficeCLIInvocationError(
                        response.message or "OfficeCLI MCP Tool执行失败"
                    )
                responses.append(response)
            except OfficeCLIInvocationError:
                raise
            except Exception as exc:
                raise OfficeCLIInvocationError("OfficeCLI真实MCP调用失败") from exc
            finally:
                transport.close()
        reference = self._output_resolver.resolve(request)
        return OfficeCLIResult(
            file_reference=reference,
            format=reference.relative_path.rsplit(".", 1)[-1],
            metadata={
                "runtime": "officecli-mcp",
                "tool": "officecli",
                "calls": len(responses),
            },
        )


def _document_content(arguments: Mapping[str, Any]) -> OfficeDocumentContent:
    content = arguments.get("content")
    if not isinstance(content, Mapping):
        raise OfficeCLIInvocationError("OfficeCLI文档内容无效")
    title = content.get("title")
    body = content.get("body", "")
    if not isinstance(title, str) or not title.strip():
        raise OfficeCLIInvocationError("OfficeCLI文档标题缺失")
    if not isinstance(body, str):
        raise OfficeCLIInvocationError("OfficeCLI文档正文无效")
    paragraphs = tuple(item.strip() for item in body.splitlines() if item.strip())
    if not paragraphs and body.strip():
        paragraphs = (body.strip(),)
    return OfficeDocumentContent(title, paragraphs)


def _required_text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise OfficeCLIInvocationError(f"OfficeCLI缺少字段：{key}")
    return item.strip()
