"""通过Service Governance访问知识能力的Knowledge Service。"""

from typing import Any, Mapping

from app.runtime.invocation_context import InvocationContext
from app.runtime.trace import generate_span_id
from app.services.governance import (
    Idempotency,
    OperationType,
    ServiceCallContext,
    ServiceCallExecutorProtocol,
    ServiceCallPolicy,
)
from app.services.models import MCPRequest, MCPResponse, ServiceResult

from .errors import (
    KNOWLEDGE_INVALID_RESPONSE,
    KNOWLEDGE_PERMISSION_DENIED,
)
from .models import (
    KnowledgeConflict,
    KnowledgeDocumentRequest,
    KnowledgeHit,
    KnowledgeMetadataData,
    KnowledgeMetadataRequest,
    KnowledgeQueryData,
    KnowledgeQueryRequest,
    KnowledgeRuntimeContext,
    KnowledgeSearchRequest,
    SourceReference,
)
from .permissions import KnowledgeAccessPolicy, KnowledgePermission


class KnowledgeService:
    """不读取文件、不导入Router，只调用固定Knowledge MCP Tool。"""

    SERVER_NAME = "knowledge-server"
    QUERY_TOOL = "knowledge.query"
    SEARCH_TOOL = "knowledge.search"
    GET_DOCUMENT_TOOL = "knowledge.get_document"
    GET_METADATA_TOOL = "knowledge.get_metadata"

    def __init__(
        self,
        governance_executor: ServiceCallExecutorProtocol,
        access_policy: KnowledgeAccessPolicy,
        governance_policy: ServiceCallPolicy,
    ) -> None:
        if governance_policy.operation_type is not OperationType.READ:
            raise ValueError("KnowledgeService治理策略必须是READ")
        if governance_policy.idempotency is not Idempotency.IDEMPOTENT:
            raise ValueError("KnowledgeService治理策略必须是IDEMPOTENT")
        self._governance_executor = governance_executor
        self._access_policy = access_policy
        self._governance_policy = governance_policy

    def query(
        self, request: KnowledgeQueryRequest
    ) -> ServiceResult[KnowledgeQueryData]:
        denied = self._authorize(
            request.runtime_context,
            KnowledgePermission.KNOWLEDGE_READ,
        )
        if denied is not None:
            return denied
        denied = self._authorize(
            request.runtime_context,
            KnowledgePermission.STANDARDS_READ,
        )
        if denied is not None:
            return denied
        response = self._call(
            "query",
            self.QUERY_TOOL,
            {"query_text": request.query_text},
            request.runtime_context,
            request.timeout,
        )
        if not response.success:
            return self._failure(response)
        try:
            payload = self._mapping(response.content)
            data = KnowledgeQueryData(
                domain_results=self._hits(payload.get("domain_results", [])),
                standards_results=self._hits(
                    payload.get("standards_results", [])
                ),
                conflicts=self._conflicts(payload.get("conflicts", [])),
            )
        except (KeyError, TypeError, ValueError):
            return self._invalid_response(request.runtime_context)
        return self._success(data, request.runtime_context)

    def search(
        self, request: KnowledgeSearchRequest
    ) -> ServiceResult[tuple[KnowledgeHit, ...]]:
        denied = self._authorize(
            request.runtime_context, KnowledgePermission.KNOWLEDGE_READ
        )
        if denied is not None:
            return denied
        denied = self._authorize(
            request.runtime_context,
            KnowledgePermission.STANDARDS_READ,
        )
        if denied is not None:
            return denied
        response = self._call(
            "search",
            self.SEARCH_TOOL,
            {"query_text": request.query_text},
            request.runtime_context,
            request.timeout,
        )
        if not response.success:
            return self._failure(response)
        try:
            data = self._hits(self._mapping(response.content).get("results", []))
        except (KeyError, TypeError, ValueError):
            return self._invalid_response(request.runtime_context)
        return self._success(data, request.runtime_context)

    def get_document(
        self, request: KnowledgeDocumentRequest
    ) -> ServiceResult[KnowledgeHit]:
        denied = self._authorize(
            request.runtime_context,
            KnowledgePermission.KNOWLEDGE_DOCUMENT_READ,
        )
        if denied is not None:
            return denied
        if request.document_id.startswith("standard."):
            denied = self._authorize(
                request.runtime_context,
                KnowledgePermission.STANDARDS_READ,
            )
            if denied is not None:
                return denied
        response = self._call(
            "get_document",
            self.GET_DOCUMENT_TOOL,
            {"document_id": request.document_id},
            request.runtime_context,
            request.timeout,
        )
        if not response.success:
            return self._failure(response)
        try:
            data = self._hit(self._mapping(response.content))
        except (KeyError, TypeError, ValueError):
            return self._invalid_response(request.runtime_context)
        return self._success(data, request.runtime_context)

    def get_metadata(
        self, request: KnowledgeMetadataRequest
    ) -> ServiceResult[KnowledgeMetadataData]:
        denied = self._authorize(
            request.runtime_context, KnowledgePermission.KNOWLEDGE_READ
        )
        if denied is not None:
            return denied
        if request.document_id.startswith("standard."):
            denied = self._authorize(
                request.runtime_context,
                KnowledgePermission.STANDARDS_READ,
            )
            if denied is not None:
                return denied
        response = self._call(
            "get_metadata",
            self.GET_METADATA_TOOL,
            {"document_id": request.document_id},
            request.runtime_context,
            request.timeout,
        )
        if not response.success:
            return self._failure(response)
        try:
            source = self._source(self._mapping(response.content))
        except (KeyError, TypeError, ValueError):
            return self._invalid_response(request.runtime_context)
        return self._success(
            KnowledgeMetadataData(source=source), request.runtime_context
        )

    def _call(
        self,
        operation_name: str,
        tool_name: str,
        arguments: Mapping[str, Any],
        context: KnowledgeRuntimeContext,
        timeout: float,
    ) -> MCPResponse:
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
            tool_name=tool_name,
            arguments=arguments,
            runtime_context=service_runtime,
            timeout=timeout,
        )
        call_context = ServiceCallContext(
            runtime_context=context,
            service_name="knowledge-service",
            operation_name=operation_name,
            service_span_id=service_span_id,
            parent_span_id=context.span_id,
            request_metadata={"tool_name": tool_name},
        )
        return self._governance_executor.execute(
            request,
            call_context,
            self._governance_policy,
        )

    def _authorize(
        self,
        context: KnowledgeRuntimeContext,
        permission: KnowledgePermission,
    ) -> ServiceResult[Any] | None:
        if self._access_policy.allows(context.skill_id, permission):
            return None
        return ServiceResult(
            success=False,
            data=None,
            error_code=KNOWLEDGE_PERMISSION_DENIED,
            message="Skill无权访问该知识能力",
            trace_id=context.trace_id,
            metadata={"span_id": context.span_id},
        )

    @staticmethod
    def _mapping(value: Any) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise TypeError("Knowledge响应必须是对象")
        return value

    @classmethod
    def _hits(cls, values: Any) -> tuple[KnowledgeHit, ...]:
        if not isinstance(values, (list, tuple)):
            raise TypeError("Knowledge结果必须是列表")
        return tuple(cls._hit(cls._mapping(value)) for value in values)

    @classmethod
    def _hit(cls, value: Mapping[str, Any]) -> KnowledgeHit:
        return KnowledgeHit(
            title=str(value["title"]),
            content=value.get("content"),
            source=cls._source(cls._mapping(value["source"])),
            status=str(value["status"]),
        )

    @staticmethod
    def _source(value: Mapping[str, Any]) -> SourceReference:
        return SourceReference(
            document_id=str(value["document_id"]),
            version=str(value["version"]),
            timestamp=str(value["timestamp"]),
            source=str(value["source"]),
            fragment_id=str(value["fragment_id"]),
            category=str(value["category"]),
        )

    @classmethod
    def _conflicts(cls, values: Any) -> tuple[KnowledgeConflict, ...]:
        if not isinstance(values, (list, tuple)):
            raise TypeError("conflicts必须是列表")
        return tuple(
            KnowledgeConflict(
                rule_key=str(value["rule_key"]),
                domain_value=str(value["domain_value"]),
                standard_value=str(value["standard_value"]),
                domain_source=cls._source(
                    cls._mapping(value["domain_source"])
                ),
                standard_source=cls._source(
                    cls._mapping(value["standard_source"])
                ),
            )
            for value in values
        )

    @staticmethod
    def _success(data: Any, context: KnowledgeRuntimeContext) -> ServiceResult[Any]:
        return ServiceResult(
            success=True,
            data=data,
            error_code=None,
            message="知识查询成功",
            trace_id=context.trace_id,
            metadata={"span_id": context.span_id},
        )

    @staticmethod
    def _failure(response: MCPResponse) -> ServiceResult[Any]:
        return ServiceResult(
            success=False,
            data=None,
            error_code=response.error_code,
            message=response.message,
            trace_id=response.trace_id,
            metadata={"span_id": response.span_id},
        )

    @staticmethod
    def _invalid_response(
        context: KnowledgeRuntimeContext,
    ) -> ServiceResult[Any]:
        return ServiceResult(
            success=False,
            data=None,
            error_code=KNOWLEDGE_INVALID_RESPONSE,
            message="Knowledge MCP响应不符合契约",
            trace_id=context.trace_id,
            metadata={"span_id": context.span_id},
        )


def _to_plain_value(value: Any) -> Any:
    """复制只读Runtime metadata，交由新InvocationContext重新冻结。"""
    if isinstance(value, Mapping):
        return {
            str(key): _to_plain_value(child)
            for key, child in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(_to_plain_value(child) for child in value)
    return value
