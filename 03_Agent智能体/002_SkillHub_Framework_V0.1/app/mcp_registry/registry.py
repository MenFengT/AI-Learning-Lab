"""MCP Server Descriptor注册、查询与固定Tool校验。"""

from .exceptions import (
    ActiveServerConflictError,
    DuplicateServerError,
    ServerDisabledError,
    ServerNotFoundError,
    ServerUnhealthyError,
    ToolNotAllowedError,
)
from .models import (
    MCPServerDescriptor,
    ServerCapability,
    ServerHealthStatus,
    ToolDescriptor,
    build_server_id,
)
from .protocols import MCPServerStoreProtocol
from .store import InMemoryMCPServerStore


class MCPServerRegistry:
    """只管理MCP Server基础设施描述，不管理连接或业务状态。"""

    def __init__(
        self, store: MCPServerStoreProtocol | None = None
    ) -> None:
        self._store = store or InMemoryMCPServerStore()

    def register(self, descriptor: MCPServerDescriptor) -> None:
        if not isinstance(descriptor, MCPServerDescriptor):
            raise TypeError("descriptor必须是MCPServerDescriptor")
        if self._store.get_by_id(descriptor.server_id) is not None:
            raise DuplicateServerError(
                f"Server已注册：{descriptor.server_id}"
            )
        if descriptor.enabled:
            active = tuple(
                item
                for item in self._store.list_all()
                if item.server_name == descriptor.server_name and item.enabled
            )
            if active:
                raise ActiveServerConflictError(
                    "同名Server只能有一个enabled版本："
                    f"{active[0].server_id}"
                )
        self._store.add(descriptor)

    def unregister(self, server_id: str) -> MCPServerDescriptor:
        return self._store.remove(server_id)

    def get(self, server_name: str) -> MCPServerDescriptor:
        matches = tuple(
            item
            for item in self._store.list_all()
            if item.server_name == server_name
        )
        if not matches:
            raise ServerNotFoundError(f"Server不存在：{server_name}")
        enabled = tuple(item for item in matches if item.enabled)
        if not enabled:
            raise ServerDisabledError(f"Server未启用：{server_name}")
        return enabled[0]

    def get_version(
        self, server_name: str, version: str
    ) -> MCPServerDescriptor:
        server_id = build_server_id(server_name, version)
        descriptor = self._store.get_by_id(server_id)
        if descriptor is None:
            raise ServerNotFoundError(f"Server不存在：{server_id}")
        return descriptor

    def list_all(self) -> tuple[MCPServerDescriptor, ...]:
        return self._store.list_all()

    def find_by_capability(
        self, capability: ServerCapability
    ) -> tuple[MCPServerDescriptor, ...]:
        if not isinstance(capability, ServerCapability):
            raise ValueError("capability必须是ServerCapability")
        return tuple(
            item
            for item in self._store.list_all()
            if item.enabled
            and item.health_status is not ServerHealthStatus.UNHEALTHY
            and item.capabilities.supports(capability)
        )

    def validate_tool(
        self, server_name: str, tool_name: str
    ) -> ToolDescriptor:
        descriptor = self.get(server_name)
        if descriptor.health_status is ServerHealthStatus.UNHEALTHY:
            raise ServerUnhealthyError(
                f"Server健康状态不可用：{server_name}"
            )
        if not descriptor.capabilities.tools:
            raise ToolNotAllowedError(
                f"Server未声明TOOLS能力：{server_name}"
            )
        tool = descriptor.tool(tool_name)
        if tool is None:
            raise ToolNotAllowedError(
                f"Tool不在固定白名单：{server_name}/{tool_name}"
            )
        return tool
