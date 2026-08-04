"""将固定Knowledge MCP Tool映射到Knowledge Router。"""

from typing import Any, Mapping

from app.knowledge import (
    KnowledgeConflict,
    KnowledgeDocument,
    KnowledgeRouter,
    SourceReference,
)
from app.mcp_servers.permissions import (
    DenyAllMCPServerPermissionPolicy,
    MCPServerPermissionPolicyProtocol,
)


class KnowledgeMCPServerAdapter:
    """固定四个Tool；不支持运行时注册或动态代码执行。"""

    ALLOWED_TOOLS = frozenset(
        {
            "knowledge.query",
            "knowledge.search",
            "knowledge.get_document",
            "knowledge.get_metadata",
        }
    )

    def __init__(
        self,
        router: KnowledgeRouter,
        permission_policy: MCPServerPermissionPolicyProtocol | None = None,
    ) -> None:
        self._router = router
        self._permission_policy = (
            permission_policy or DenyAllMCPServerPermissionPolicy()
        )

    def handle(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            if payload.get("method") != "tools/call":
                return self._error(
                    "SHF-KNW-REQUEST-INVALID", "只支持tools/call"
                )
            params = self._mapping(payload.get("params"))
            tool_name = params.get("name")
            if tool_name not in self.ALLOWED_TOOLS:
                return self._error(
                    "SHF-MCP-TOOL-NOT_FOUND", "Knowledge Tool不存在"
                )
            arguments = self._mapping(params.get("arguments", {}))
            context = self._mapping(params.get("_meta"))
            self._validate_runtime_context(context)
            self._authorize(str(tool_name), arguments, context)

            if tool_name == "knowledge.query":
                return {"content": self._query(arguments)}
            if tool_name == "knowledge.search":
                return {"content": self._search(arguments)}
            if tool_name == "knowledge.get_document":
                return {"content": self._get_document(arguments)}
            if tool_name == "knowledge.get_metadata":
                return {"content": self._get_metadata(arguments)}
            return self._error(
                "SHF-MCP-TOOL-NOT_FOUND", "Knowledge Tool不存在"
            )
        except KeyError:
            return self._error(
                "SHF-SVC-KNOWLEDGE-NOT_FOUND", "知识文档不存在"
            )
        except PermissionError:
            return self._error(
                "SHF-MCP-AUTH-PERMISSION_DENIED",
                "Knowledge Tool权限不足",
            )
        except (TypeError, ValueError):
            return self._error(
                "SHF-KNW-REQUEST-INVALID", "Knowledge请求无效"
            )

    def _authorize(
        self,
        tool_name: str,
        arguments: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> None:
        skill_id = str(context["skill_id"])
        required = {"KNOWLEDGE_READ"}
        if tool_name == "knowledge.get_document":
            required.add("KNOWLEDGE_DOCUMENT_READ")
        if tool_name in {"knowledge.query", "knowledge.search"}:
            required.add("STANDARDS_READ")
        document_id = arguments.get("document_id")
        if isinstance(document_id, str) and document_id.startswith("standard."):
            required.add("STANDARDS_READ")
        if any(
            not self._permission_policy.allows(skill_id, permission)
            for permission in required
        ):
            raise PermissionError("Skill无权直接调用Knowledge MCP Tool")

    def _query(self, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        query_text = self._required_text(arguments, "query_text")
        result = self._router.query(query_text)
        return {
            "domain_results": [
                self._document(item) for item in result.domain_results
            ],
            "standards_results": [
                self._document(item) for item in result.standards_results
            ],
            "conflicts": [self._conflict(item) for item in result.conflicts],
            "query_strategy": "DOMAIN_THEN_STANDARDS",
        }

    def _search(self, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        query_text = self._required_text(arguments, "query_text")
        return {
            "results": [
                self._document(item) for item in self._router.search(query_text)
            ]
        }

    def _get_document(self, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        document_id = self._required_document_id(arguments)
        return self._document(self._router.get_document(document_id))

    def _get_metadata(self, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        document_id = self._required_document_id(arguments)
        return self._source(self._router.get_metadata(document_id))

    @staticmethod
    def _document(document: KnowledgeDocument) -> Mapping[str, Any]:
        return {
            "title": document.title,
            "content": document.content,
            "source": KnowledgeMCPServerAdapter._source(document.source),
            "status": document.status,
        }

    @staticmethod
    def _source(source: SourceReference) -> Mapping[str, Any]:
        return {
            "document_id": source.document_id,
            "version": source.version,
            "timestamp": source.timestamp,
            "source": source.source,
            "fragment_id": source.fragment_id,
            "category": source.category.value,
        }

    @staticmethod
    def _conflict(conflict: KnowledgeConflict) -> Mapping[str, Any]:
        return {
            "rule_key": conflict.rule_key,
            "domain_value": conflict.domain_value,
            "standard_value": conflict.standard_value,
            "domain_source": KnowledgeMCPServerAdapter._source(
                conflict.domain_source
            ),
            "standard_source": KnowledgeMCPServerAdapter._source(
                conflict.standard_source
            ),
        }

    @staticmethod
    def _required_text(arguments: Mapping[str, Any], key: str) -> str:
        value = arguments.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key}不能为空")
        return value.strip()

    @classmethod
    def _required_document_id(cls, arguments: Mapping[str, Any]) -> str:
        if "path" in arguments or "file_path" in arguments:
            raise ValueError("禁止直接文件路径")
        return cls._required_text(arguments, "document_id")

    @staticmethod
    def _validate_runtime_context(context: Mapping[str, Any]) -> None:
        for field in ("task_id", "trace_id", "span_id", "skill_id"):
            value = context.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"缺少Runtime Context：{field}")

    @staticmethod
    def _mapping(value: Any) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise TypeError("MCP字段必须是对象")
        return value

    @staticmethod
    def _error(error_code: str, message: str) -> Mapping[str, Any]:
        return {"is_error": True, "error_code": error_code, "message": message}
