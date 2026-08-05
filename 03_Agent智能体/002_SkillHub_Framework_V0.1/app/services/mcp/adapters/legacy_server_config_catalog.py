"""旧ServerConfig Mapping到新Registry契约的兼容适配器。"""

from types import MappingProxyType
from typing import Mapping

from app.mcp_registry import (
    MCPServerDescriptor,
    MCPServerRegistry,
    ServerCapabilities,
    ServerCapability,
    ServerHealthStatus,
    ToolDescriptor,
    ToolIdempotency,
    TransportType,
    build_server_id,
)

from ..errors import MCPServerConfigurationError
from ..models import ServerConfig


class LegacyServerConfigCatalogAdapter:
    """兼容旧配置；不创建连接、不保存Secret、不执行Tool。"""

    LEGACY_VERSION = "0.1.0"

    def __init__(self, server_configs: Mapping[str, ServerConfig]) -> None:
        configs = dict(server_configs)
        self._registry = MCPServerRegistry()
        references: dict[str, ServerConfig] = {}
        for server_name, config in configs.items():
            if server_name != config.server_name:
                raise MCPServerConfigurationError(
                    "ServerConfig键与server_name不一致"
                )
            reference = f"legacy.{server_name}.v0_1"
            descriptor = MCPServerDescriptor(
                server_id=build_server_id(
                    server_name, self.LEGACY_VERSION
                ),
                server_name=server_name,
                version=self.LEGACY_VERSION,
                description=f"Legacy ServerConfig adapter for {server_name}",
                transport_type=_transport_type(config.transport_name),
                transport_config_reference=reference,
                capabilities=ServerCapabilities(tools=True),
                allowed_tools=tuple(
                    ToolDescriptor(
                        tool_name=tool_name,
                        description=f"Legacy fixed tool {tool_name}",
                        input_schema={"type": "object"},
                        output_schema={"type": "object"},
                        permission_required="LEGACY_MCP_CALL",
                        idempotency=ToolIdempotency.NON_IDEMPOTENT,
                    )
                    for tool_name in sorted(config.allowed_tools)
                ),
                health_status=ServerHealthStatus.UNKNOWN,
                enabled=config.enabled,
                metadata={"source": "legacy-server-config"},
            )
            self._registry.register(descriptor)
            references[reference] = config
        self._configs = MappingProxyType(references)

    def get(self, server_name: str) -> MCPServerDescriptor:
        return self._registry.get(server_name)

    def get_version(
        self, server_name: str, version: str
    ) -> MCPServerDescriptor:
        return self._registry.get_version(server_name, version)

    def list_all(self) -> tuple[MCPServerDescriptor, ...]:
        return self._registry.list_all()

    def find_by_capability(
        self, capability: ServerCapability
    ) -> tuple[MCPServerDescriptor, ...]:
        return self._registry.find_by_capability(capability)

    def validate_tool(
        self, server_name: str, tool_name: str
    ) -> ToolDescriptor:
        return self._registry.validate_tool(server_name, tool_name)

    def resolve(self, transport_config_reference: str) -> ServerConfig:
        try:
            return self._configs[transport_config_reference]
        except KeyError as exc:
            raise MCPServerConfigurationError(
                "Transport配置引用不存在"
            ) from exc


def _transport_type(transport_name: str) -> TransportType:
    normalized = transport_name.casefold()
    if normalized == "stdio":
        return TransportType.STDIO
    if normalized == "http":
        return TransportType.HTTP
    if normalized == "sse":
        return TransportType.SSE
    return TransportType.IN_MEMORY
