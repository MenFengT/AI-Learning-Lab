"""Composition Root可注入的OfficeCLI官方SDK Transport Provider。"""

from typing import Any, Callable

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from .sdk_transport import OfficeCLIMCPTransport, OfficeCLIMCPTransportConfig


class OfficeCLIMCPTransportProvider:
    def __init__(
        self,
        config: OfficeCLIMCPTransportConfig,
        *,
        stdio_factory: Callable[..., Any] = stdio_client,
        session_factory: Callable[..., Any] = ClientSession,
    ) -> None:
        if not isinstance(config, OfficeCLIMCPTransportConfig):
            raise TypeError("config必须是OfficeCLIMCPTransportConfig")
        self._config = config
        self._stdio_factory = stdio_factory
        self._session_factory = session_factory

    def create(self) -> OfficeCLIMCPTransport:
        return OfficeCLIMCPTransport(
            self._config,
            stdio_factory=self._stdio_factory,
            session_factory=self._session_factory,
        )
