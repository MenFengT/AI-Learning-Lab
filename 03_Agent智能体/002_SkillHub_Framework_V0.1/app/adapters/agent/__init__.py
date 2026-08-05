"""Agent Gateway Adapter 公共契约。"""

from .adapter import AgentAdapter
from .errors import (
    AgentAdapterError,
    AgentInvocationError,
    AgentRequestConversionError,
    AgentResultConversionError,
)
from .models import AgentAttachmentInput, AgentTaskInput, AgentTaskResult
from .protocols import AgentGatewayAdapterProtocol, AgentRuntimeInvocationProtocol

__all__ = [
    "AgentAdapter",
    "AgentAdapterError",
    "AgentAttachmentInput",
    "AgentGatewayAdapterProtocol",
    "AgentInvocationError",
    "AgentRequestConversionError",
    "AgentResultConversionError",
    "AgentRuntimeInvocationProtocol",
    "AgentTaskInput",
    "AgentTaskResult",
]
