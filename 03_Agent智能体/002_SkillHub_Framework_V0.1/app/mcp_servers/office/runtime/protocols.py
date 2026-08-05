"""Composition Root 注入的 OfficeCLI Runtime API。"""

from typing import Protocol, runtime_checkable

from .models import OfficeCLIRequest, OfficeCLIResult


@runtime_checkable
class OfficeCLIRuntimeProtocol(Protocol):
    """固定方法 API；禁止接收命令行字符串。"""

    def create_document(self, request: OfficeCLIRequest) -> OfficeCLIResult: ...

    def update_document(self, request: OfficeCLIRequest) -> OfficeCLIResult: ...

    def convert_document(self, request: OfficeCLIRequest) -> OfficeCLIResult: ...

    def export_document(self, request: OfficeCLIRequest) -> OfficeCLIResult: ...
