"""MCP Server Registry公开接口。"""

from .exceptions import (
    ActiveServerConflictError,
    DescriptorValidationError,
    DuplicateServerError,
    MCPRegistryError,
    SecretDetectedError,
    ServerDisabledError,
    ServerNotFoundError,
    ServerUnhealthyError,
    ToolNotAllowedError,
)
from .health import HealthCheckResult, check_server_health
from .models import (
    MCPServerDescriptor,
    ServerCapabilities,
    ServerCapability,
    ServerHealthStatus,
    ToolDescriptor,
    ToolIdempotency,
    TransportType,
    build_server_id,
)
from .protocols import (
    MCPServerCatalogProtocol,
    MCPServerStoreProtocol,
    TransportAvailabilityProtocol,
)
from .registry import MCPServerRegistry
from .store import InMemoryMCPServerStore

__all__ = [
    "ActiveServerConflictError",
    "DescriptorValidationError",
    "DuplicateServerError",
    "HealthCheckResult",
    "InMemoryMCPServerStore",
    "MCPRegistryError",
    "MCPServerCatalogProtocol",
    "MCPServerDescriptor",
    "MCPServerRegistry",
    "MCPServerStoreProtocol",
    "SecretDetectedError",
    "ServerCapabilities",
    "ServerCapability",
    "ServerDisabledError",
    "ServerHealthStatus",
    "ServerNotFoundError",
    "ServerUnhealthyError",
    "ToolDescriptor",
    "ToolIdempotency",
    "ToolNotAllowedError",
    "TransportAvailabilityProtocol",
    "TransportType",
    "build_server_id",
    "check_server_health",
]
