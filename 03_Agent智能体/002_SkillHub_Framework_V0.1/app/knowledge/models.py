"""Knowledge Router内部的可审计知识模型。"""

from dataclasses import dataclass
from enum import Enum


class KnowledgeCategory(str, Enum):
    DOMAIN = "DOMAIN"
    STANDARD = "STANDARD"


@dataclass(frozen=True)
class SourceReference:
    document_id: str
    version: str
    timestamp: str
    source: str
    fragment_id: str
    category: KnowledgeCategory


@dataclass(frozen=True)
class KnowledgeDocument:
    title: str
    content: str
    source: SourceReference
    status: str = "ACTIVE"


@dataclass(frozen=True)
class KnowledgeConflict:
    rule_key: str
    domain_value: str
    standard_value: str
    domain_source: SourceReference
    standard_source: SourceReference


@dataclass(frozen=True)
class KnowledgeQueryResult:
    domain_results: tuple[KnowledgeDocument, ...]
    standards_results: tuple[KnowledgeDocument, ...]
    conflicts: tuple[KnowledgeConflict, ...]
