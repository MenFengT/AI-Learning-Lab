"""统一知识访问模块。"""

from .knowledge_router import KnowledgeRouter

__all__ = ["KnowledgeRouter"]
from .knowledge_router import KnowledgeRouter
from .models import (
    KnowledgeCategory,
    KnowledgeConflict,
    KnowledgeDocument,
    KnowledgeQueryResult,
    SourceReference,
)

__all__ = [
    "KnowledgeCategory",
    "KnowledgeConflict",
    "KnowledgeDocument",
    "KnowledgeQueryResult",
    "KnowledgeRouter",
    "SourceReference",
]
