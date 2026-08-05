"""MCP Transport连接生命周期管理。"""

from contextlib import contextmanager
from types import MappingProxyType
from typing import Iterator, Mapping

from .errors import MCPServerConfigurationError
from .models import ServerConfig
from .protocols import MCPTransportFactoryProtocol, MCPTransportProtocol


class ConnectionManager:
    """按Transport名称创建连接，并保证离开作用域时释放资源。"""

    def __init__(
        self,
        transport_factories: Mapping[str, MCPTransportFactoryProtocol],
    ) -> None:
        self._transport_factories = MappingProxyType(dict(transport_factories))

    @contextmanager
    def connection(
        self, config: ServerConfig
    ) -> Iterator[MCPTransportProtocol]:
        factory = self._transport_factories.get(config.transport_name)
        if factory is None:
            raise MCPServerConfigurationError(
                f"未配置Transport：{config.transport_name}"
            )
        transport = factory()
        try:
            transport.connect(config)
            yield transport
        finally:
            transport.close()
