"""Document Automation Skill稳定数据契约。"""

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from app.services.office.models import (
    OfficeDocumentRequest,
    OfficeDocumentResult,
)


class DocumentType(str, Enum):
    PROPOSAL = "proposal"
    REPORT = "report"
    PAPER = "paper"


@dataclass(frozen=True)
class DocumentRequest:
    document_type: DocumentType
    title: str
    output_name: str
    requirements: str
    sections: tuple[str, ...] = ()
    knowledge_query: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.document_type, DocumentType):
            raise ValueError("document_type必须为DocumentType")
        for label in ("title", "output_name", "requirements"):
            value = getattr(self, label)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label}不能为空")
        sections = tuple(section.strip() for section in self.sections)
        if any(not section for section in sections):
            raise ValueError("sections不能包含空值")
        if self.knowledge_query is not None and not self.knowledge_query.strip():
            raise ValueError("knowledge_query不能为空字符串")
        object.__setattr__(self, "sections", sections)
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(deepcopy(dict(self.metadata))),
        )


@dataclass(frozen=True)
class DocumentSection:
    heading: str
    guidance: str


@dataclass(frozen=True)
class DocumentContent:
    title: str
    requirements: str
    prompt_template: str
    sections: tuple[DocumentSection, ...]
    knowledge_fragments: tuple[str, ...] = ()
