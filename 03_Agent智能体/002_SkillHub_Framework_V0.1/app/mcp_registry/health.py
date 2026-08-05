"""不连接Server、不执行业务Tool的MCP Descriptor健康检查。"""

from dataclasses import dataclass

from .exceptions import DescriptorValidationError
from .models import (
    MCPServerDescriptor,
    ServerHealthStatus,
    validate_transport_reference,
    validate_version,
)
from .protocols import TransportAvailabilityProtocol


@dataclass(frozen=True)
class HealthCheckResult:
    server_id: str
    status: ServerHealthStatus
    checks: tuple[str, ...]
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def check_server_health(
    descriptor: MCPServerDescriptor,
    transport_availability: TransportAvailabilityProtocol,
) -> HealthCheckResult:
    """只验证Descriptor、能力和Transport引用是否可用。"""
    checks: list[str] = []
    errors: list[str] = []
    try:
        validate_version(descriptor.version)
        checks.append("version")
        validate_transport_reference(descriptor.transport_config_reference)
        checks.append("transport_reference")
        if descriptor.capabilities.tools and not descriptor.allowed_tools:
            errors.append("TOOLS能力缺少Tool描述")
        else:
            checks.append("capabilities")
        if len({tool.tool_name for tool in descriptor.allowed_tools}) != len(
            descriptor.allowed_tools
        ):
            errors.append("Tool名称重复")
        else:
            checks.append("tools")
    except DescriptorValidationError as exc:
        errors.append(str(exc))

    try:
        transport_supported = transport_availability.supports(
            descriptor.transport_type.value,
            descriptor.transport_config_reference,
        )
    except Exception as exc:
        transport_supported = False
        errors.append(
            "Transport可用性检查失败："
            f"{type(exc).__name__}"
        )
    if transport_supported:
        checks.append("transport_available")
    else:
        errors.append("Transport类型或配置引用不可用")

    status = (
        ServerHealthStatus.HEALTHY
        if not errors
        else ServerHealthStatus.UNHEALTHY
    )
    return HealthCheckResult(
        server_id=descriptor.server_id,
        status=status,
        checks=tuple(checks),
        errors=tuple(errors),
    )
