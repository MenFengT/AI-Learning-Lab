"""Agent Gateway Adapter 端口定义。"""

from typing import Protocol, runtime_checkable

from app.gateway.models import AgentInvocationResult, UserMessage

from .models import AgentTaskInput, AgentTaskResult


@runtime_checkable
class AgentRuntimeInvocationProtocol(Protocol):
    """由 Composition Root 注入的真实 Agent Runtime 调用端口。"""

    def invoke(self, task: AgentTaskInput) -> AgentTaskResult: ...


@runtime_checkable
class AgentGatewayAdapterProtocol(Protocol):
    """Gateway 所依赖的 Agent 调用适配器契约。"""

    def invoke(self, message: UserMessage) -> AgentInvocationResult: ...
