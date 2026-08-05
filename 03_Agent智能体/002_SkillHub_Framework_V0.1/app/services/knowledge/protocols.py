"""Skill唯一允许依赖的Knowledge Service接口。"""

from typing import Protocol, runtime_checkable

from app.services.models import ServiceResult

from .models import (
    KnowledgeDocumentRequest,
    KnowledgeHit,
    KnowledgeMetadataData,
    KnowledgeMetadataRequest,
    KnowledgeQueryData,
    KnowledgeQueryRequest,
    KnowledgeSearchRequest,
)


@runtime_checkable
class KnowledgeServiceProtocol(Protocol):
    def query(
        self, request: KnowledgeQueryRequest
    ) -> ServiceResult[KnowledgeQueryData]: ...

    def search(
        self, request: KnowledgeSearchRequest
    ) -> ServiceResult[tuple[KnowledgeHit, ...]]: ...

    def get_document(
        self, request: KnowledgeDocumentRequest
    ) -> ServiceResult[KnowledgeHit]: ...

    def get_metadata(
        self, request: KnowledgeMetadataRequest
    ) -> ServiceResult[KnowledgeMetadataData]: ...
