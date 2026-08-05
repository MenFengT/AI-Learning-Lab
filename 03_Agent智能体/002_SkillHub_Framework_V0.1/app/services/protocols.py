"""Service Layer通用协议及历史导入路径的兼容导出。"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class RuntimeContextProtocol(Protocol):
    """Service所需的最小Runtime上下文投影。"""

    task_id: str
    trace_id: str
    span_id: str
    skill_id: str


@runtime_checkable
class ServiceConfigProtocol(Protocol):
    """Service使用的类型化配置视图，不提供任意依赖查找。"""

    default_timeout_seconds: float
    max_timeout_seconds: float


# 在通用协议定义完成后加载能力协议，避免MCP模型回引Runtime协议时形成循环。
from .audit.protocols import AuditServiceProtocol  # noqa: E402
from .mcp.protocols import MCPClientProtocol  # noqa: E402


__all__ = [
    "AuditServiceProtocol",
    "MCPClientProtocol",
    "RuntimeContextProtocol",
    "ServiceConfigProtocol",
]
