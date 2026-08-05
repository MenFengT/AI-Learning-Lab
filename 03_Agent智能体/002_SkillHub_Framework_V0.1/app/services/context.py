"""Service Layer基础设施依赖上下文。"""

from dataclasses import dataclass

from .protocols import (
    AuditServiceProtocol,
    MCPClientProtocol,
    RuntimeContextProtocol,
    ServiceConfigProtocol,
)


@dataclass(frozen=True)
class ServiceContext:
    """由Composition Root注入依赖，不保存业务状态。"""

    mcp_client: MCPClientProtocol
    audit_service: AuditServiceProtocol
    runtime_context: RuntimeContextProtocol
    config: ServiceConfigProtocol

    def __post_init__(self) -> None:
        if not self.runtime_context.task_id.strip():
            raise ValueError("runtime_context.task_id不能为空")
        if not self.runtime_context.trace_id.strip():
            raise ValueError("runtime_context.trace_id不能为空")
        if not self.runtime_context.span_id.strip():
            raise ValueError("runtime_context.span_id不能为空")
        if not self.runtime_context.skill_id.strip():
            raise ValueError("runtime_context.skill_id不能为空")
        if self.config.default_timeout_seconds <= 0:
            raise ValueError("default_timeout_seconds必须大于0")
        if self.config.max_timeout_seconds < self.config.default_timeout_seconds:
            raise ValueError("max_timeout_seconds不能小于默认超时")
