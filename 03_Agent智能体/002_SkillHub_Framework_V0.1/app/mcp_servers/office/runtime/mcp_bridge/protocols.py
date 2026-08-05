"""OfficeCLI MCP Bridge 与外部Transport端口。"""

from typing import Protocol, runtime_checkable

from app.mcp_servers.office.runtime.models import OfficeCLIRequest, OfficeCLIResult

from .models import OfficeCLIMCPCall, OfficeCLIMCPResult


@runtime_checkable
class ExternalMCPTransportProtocol(Protocol):
    """由外部实现管理网络协议；不接收命令行或文件路径。"""

    def connect(self) -> None: ...

    def call(self, request: OfficeCLIMCPCall) -> OfficeCLIMCPResult: ...

    def close(self) -> None: ...


@runtime_checkable
class TransportProviderProtocol(Protocol):
    """每次Bridge调用创建独立Transport，具体实现由Composition Root注入。"""

    def create(self) -> ExternalMCPTransportProtocol: ...


@runtime_checkable
class OfficeCLIMCPBridgeProtocol(Protocol):
    def create_document(self, request: OfficeCLIRequest) -> OfficeCLIResult: ...

    def update_document(self, request: OfficeCLIRequest) -> OfficeCLIResult: ...

    def convert_document(self, request: OfficeCLIRequest) -> OfficeCLIResult: ...

    def export_document(self, request: OfficeCLIRequest) -> OfficeCLIResult: ...
