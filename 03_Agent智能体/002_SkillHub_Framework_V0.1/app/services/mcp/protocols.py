"""MCP Client和Transport协议。"""

from typing import Any, Mapping, Protocol, runtime_checkable

from app.services.models import MCPRequest, MCPResponse

from .models import ServerConfig


@runtime_checkable
class MCPClientProtocol(Protocol):
    def call(self, request: MCPRequest) -> MCPResponse: ...


@runtime_checkable
class TransportConfigProviderProtocol(Protocol):
    """按非敏感配置引用解析连接配置。"""

    def resolve(self, transport_config_reference: str) -> ServerConfig: ...


@runtime_checkable
class MCPTransportProtocol(Protocol):
    """单次连接和协议通信接口，不包含重试。"""

    def connect(self, config: ServerConfig) -> None: ...

    def send(
        self, payload: Mapping[str, Any], timeout: float
    ) -> Mapping[str, Any]: ...

    def close(self) -> None: ...

    def is_connected(self) -> bool: ...


@runtime_checkable
class MCPTransportFactoryProtocol(Protocol):
    def __call__(self) -> MCPTransportProtocol: ...
