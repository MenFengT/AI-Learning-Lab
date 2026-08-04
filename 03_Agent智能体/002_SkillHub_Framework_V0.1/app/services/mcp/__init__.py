"""通用MCP Client Infrastructure公开接口。"""

from .client import MCPClient
from .adapters import LegacyServerConfigCatalogAdapter
from .connection_manager import ConnectionManager
from .errors import (
    MCPInfrastructureError,
    MCPServerConfigurationError,
    MCPToolNotAllowedError,
    MCPTransportConnectionError,
    MCPTransportError,
    MCPTransportProtocolError,
    MCPTransportTimeoutError,
)
from .models import ServerConfig
from .protocols import (
    MCPClientProtocol,
    MCPTransportProtocol,
    TransportConfigProviderProtocol,
)
from .transport import FakeTransport

__all__ = [
    "ConnectionManager",
    "FakeTransport",
    "MCPClient",
    "MCPClientProtocol",
    "MCPInfrastructureError",
    "LegacyServerConfigCatalogAdapter",
    "MCPServerConfigurationError",
    "MCPToolNotAllowedError",
    "MCPTransportConnectionError",
    "MCPTransportError",
    "MCPTransportProtocol",
    "MCPTransportProtocolError",
    "MCPTransportTimeoutError",
    "ServerConfig",
    "TransportConfigProviderProtocol",
]
