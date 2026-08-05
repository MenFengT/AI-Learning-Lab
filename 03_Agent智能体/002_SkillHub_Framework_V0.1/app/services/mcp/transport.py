"""无外部通信的Fake Transport，用于契约与单元测试。"""

from copy import deepcopy
from typing import Any, Mapping

from .errors import MCPTransportConnectionError
from .models import ServerConfig


class FakeTransport:
    """可注入响应或异常的确定性Transport，不执行网络或Shell。"""

    def __init__(
        self,
        response: Mapping[str, Any] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._response = deepcopy(dict(response or {"content": None}))
        self._error = error
        self._connected = False
        self.connect_count = 0
        self.send_count = 0
        self.close_count = 0
        self.last_config: ServerConfig | None = None
        self.last_payload: Mapping[str, Any] | None = None
        self.last_timeout: float | None = None

    def connect(self, config: ServerConfig) -> None:
        self.connect_count += 1
        self.last_config = config
        self._connected = True

    def send(
        self, payload: Mapping[str, Any], timeout: float
    ) -> Mapping[str, Any]:
        if not self._connected:
            raise MCPTransportConnectionError("Transport尚未连接")
        self.send_count += 1
        self.last_payload = deepcopy(dict(payload))
        self.last_timeout = timeout
        if self._error is not None:
            raise self._error
        return deepcopy(self._response)

    def close(self) -> None:
        self.close_count += 1
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected
