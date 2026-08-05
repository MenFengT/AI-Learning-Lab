"""Construction Document Skill 允许依赖的协议。"""

from typing import Protocol, runtime_checkable

from app.services.content.protocols import ContentServiceProtocol
from app.services.knowledge.protocols import KnowledgeServiceProtocol

from .models import ConstructionDocumentTemplate, ConstructionDocumentType


@runtime_checkable
class ConstructionTemplateProviderProtocol(Protocol):
    def load(self, document_type: ConstructionDocumentType) -> ConstructionDocumentTemplate: ...


__all__ = [
    "ConstructionTemplateProviderProtocol",
    "ContentServiceProtocol",
    "KnowledgeServiceProtocol",
]
