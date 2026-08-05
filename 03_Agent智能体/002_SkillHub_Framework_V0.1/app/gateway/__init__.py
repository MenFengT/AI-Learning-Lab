"""Interaction Gateway公共契约。"""

from .errors import GatewayError, GatewayInvocationError, GatewayValidationError
from .models import (
    AgentArtifactReference,
    AgentInvocationResult,
    AgentResponse,
    AsyncTaskStatus,
    Attachment,
    AttachmentType,
    UserMessage,
)
from .protocols import AgentInvocationProtocol, InteractionGatewayProtocol
from .service import InteractionGateway

__all__ = [
    "AgentArtifactReference",
    "AgentInvocationProtocol",
    "AgentInvocationResult",
    "AgentResponse",
    "AsyncTaskStatus",
    "Attachment",
    "AttachmentType",
    "GatewayError",
    "GatewayInvocationError",
    "GatewayValidationError",
    "InteractionGateway",
    "InteractionGatewayProtocol",
    "UserMessage",
]
