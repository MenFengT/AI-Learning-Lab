"""用户消息到Agent调用契约的无状态适配器。"""

from .errors import GatewayInvocationError
from .models import AgentResponse, UserMessage
from .protocols import AgentInvocationProtocol


class InteractionGateway:
    """只转换消息和标准化结果，不控制Agent或任务生命周期。"""

    def __init__(self, agent_invocation: AgentInvocationProtocol) -> None:
        self._agent_invocation = agent_invocation

    def handle(self, message: UserMessage) -> AgentResponse:
        if not isinstance(message, UserMessage):
            raise TypeError("message必须为UserMessage")
        try:
            result = self._agent_invocation.invoke(message)
        except Exception as exc:
            raise GatewayInvocationError("Agent调用适配失败") from exc
        return AgentResponse(
            task_id=result.task_id,
            status=result.status,
            message=result.message,
            artifacts=result.artifacts,
            metadata=result.metadata,
        )
