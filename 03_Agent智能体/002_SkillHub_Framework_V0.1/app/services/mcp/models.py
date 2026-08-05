"""MCP Server和Transport配置模型。"""

from dataclasses import dataclass
import re


_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*$")


@dataclass(frozen=True)
class ServerConfig:
    """由受控配置创建的MCP Server连接描述。"""

    server_name: str
    transport_name: str
    allowed_tools: frozenset[str]
    connect_timeout: float
    max_request_timeout: float
    enabled: bool = True

    def __post_init__(self) -> None:
        _validate_name(self.server_name, "server_name")
        _validate_name(self.transport_name, "transport_name")
        if not self.allowed_tools:
            raise ValueError("allowed_tools不能为空")
        for tool_name in self.allowed_tools:
            _validate_name(tool_name, "tool_name")
        if self.connect_timeout <= 0:
            raise ValueError("connect_timeout必须大于0")
        if self.max_request_timeout <= 0:
            raise ValueError("max_request_timeout必须大于0")


def _validate_name(value: str, label: str) -> None:
    if not _NAME_PATTERN.fullmatch(value):
        raise ValueError(f"{label}必须是受控小写标识符：{value}")
