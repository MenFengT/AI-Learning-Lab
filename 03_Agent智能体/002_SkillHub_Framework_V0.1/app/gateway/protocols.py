"""Interaction Gateway与Agent适配端口。"""

from typing import Protocol, runtime_checkable

from .models import AgentInvocationResult, AgentResponse, UserMessage


@runtime_checkable
class AgentInvocationProtocol(Protocol):
    """由Composition Root提供；Gateway不依赖具体Agent。"""

    def invoke(self, message: UserMessage) -> AgentInvocationResult: ...


@runtime_checkable
class InteractionGatewayProtocol(Protocol):
    def handle(self, message: UserMessage) -> AgentResponse: ...
