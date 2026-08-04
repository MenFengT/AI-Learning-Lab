"""Skill可依赖的Knowledge Service稳定数据契约。"""

from dataclasses import dataclass, field
from typing import Any, Mapping

from app.runtime.invocation_context import InvocationContext


@dataclass(frozen=True)
class KnowledgeRuntimeContext(InvocationContext):
    """Knowledge旧上下文名称的兼容类型，统一遵循InvocationContext。"""


@dataclass(frozen=True)
class SourceReference:
    document_id: str
    version: str
    timestamp: str
    source: str
    fragment_id: str
    category: str


@dataclass(frozen=True)
class KnowledgeHit:
    title: str
    content: str | None
    source: SourceReference
    status: str


@dataclass(frozen=True)
class KnowledgeConflict:
    rule_key: str
    domain_value: str
    standard_value: str
    domain_source: SourceReference
    standard_source: SourceReference


@dataclass(frozen=True)
class KnowledgeQueryData:
    domain_results: tuple[KnowledgeHit, ...]
    standards_results: tuple[KnowledgeHit, ...]
    conflicts: tuple[KnowledgeConflict, ...]
    query_strategy: str = "DOMAIN_THEN_STANDARDS"


@dataclass(frozen=True)
class KnowledgeQueryRequest:
    runtime_context: KnowledgeRuntimeContext
    query_text: str
    timeout: float


@dataclass(frozen=True)
class KnowledgeSearchRequest:
    runtime_context: KnowledgeRuntimeContext
    query_text: str
    timeout: float


@dataclass(frozen=True)
class KnowledgeDocumentRequest:
    runtime_context: KnowledgeRuntimeContext
    document_id: str
    timeout: float


@dataclass(frozen=True)
class KnowledgeMetadataRequest:
    runtime_context: KnowledgeRuntimeContext
    document_id: str
    timeout: float


@dataclass(frozen=True)
class KnowledgeMetadataData:
    source: SourceReference
    metadata: Mapping[str, Any] = field(default_factory=dict)
