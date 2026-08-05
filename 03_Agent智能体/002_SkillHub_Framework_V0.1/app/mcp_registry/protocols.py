"""MCP Server Registry只读目录与存储协议。"""

from typing import Protocol, runtime_checkable

from .models import (
    MCPServerDescriptor,
    ServerCapability,
    ToolDescriptor,
)


@runtime_checkable
class MCPServerStoreProtocol(Protocol):
    def add(self, descriptor: MCPServerDescriptor) -> None: ...

    def remove(self, server_id: str) -> MCPServerDescriptor: ...

    def get_by_id(self, server_id: str) -> MCPServerDescriptor | None: ...

    def list_all(self) -> tuple[MCPServerDescriptor, ...]: ...


@runtime_checkable
class MCPServerCatalogProtocol(Protocol):
    def get(self, server_name: str) -> MCPServerDescriptor: ...

    def get_version(
        self, server_name: str, version: str
    ) -> MCPServerDescriptor: ...

    def list_all(self) -> tuple[MCPServerDescriptor, ...]: ...

    def find_by_capability(
        self, capability: ServerCapability
    ) -> tuple[MCPServerDescriptor, ...]: ...

    def validate_tool(
        self, server_name: str, tool_name: str
    ) -> ToolDescriptor: ...


@runtime_checkable
class TransportAvailabilityProtocol(Protocol):
    def supports(
        self, transport_type: str, transport_config_reference: str
    ) -> bool: ...
