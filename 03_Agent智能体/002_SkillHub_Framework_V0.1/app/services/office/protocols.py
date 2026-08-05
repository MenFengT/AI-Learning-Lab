"""Skill唯一允许依赖的Office Service协议。"""

from typing import Protocol, runtime_checkable

from app.services.models import ServiceResult

from .models import OfficeDocumentRequest, OfficeDocumentResult


@runtime_checkable
class OfficeServiceProtocol(Protocol):
    def create_document(
        self, request: OfficeDocumentRequest
    ) -> ServiceResult[OfficeDocumentResult]: ...

    def update_document(
        self, request: OfficeDocumentRequest
    ) -> ServiceResult[OfficeDocumentResult]: ...

    def convert_document(
        self, request: OfficeDocumentRequest
    ) -> ServiceResult[OfficeDocumentResult]: ...

    def export_document(
        self, request: OfficeDocumentRequest
    ) -> ServiceResult[OfficeDocumentResult]: ...
