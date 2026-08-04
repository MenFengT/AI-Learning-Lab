"""SkillHub Service Layer基础数据契约。"""

from .context import ServiceContext
from .errors import (
    ErrorDescriptor,
    ErrorSeverity,
    ServiceLayerError,
    validate_error_code,
)
from .models import MCPRequest, MCPResponse, ServiceResult
from .protocols import (
    AuditServiceProtocol,
    MCPClientProtocol,
    RuntimeContextProtocol,
    ServiceConfigProtocol,
)

__all__ = [
    "AuditServiceProtocol",
    "ErrorDescriptor",
    "ErrorSeverity",
    "MCPClientProtocol",
    "MCPRequest",
    "MCPResponse",
    "RuntimeContextProtocol",
    "ServiceConfigProtocol",
    "ServiceContext",
    "ServiceLayerError",
    "ServiceResult",
    "validate_error_code",
]
