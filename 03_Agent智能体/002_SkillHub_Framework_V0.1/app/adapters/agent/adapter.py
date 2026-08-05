"""Gateway 请求到 Agent Runtime 协议的无状态转换适配器。"""

from app.gateway.models import AgentInvocationResult, Attachment, UserMessage

from .errors import (
    AgentInvocationError,
    AgentRequestConversionError,
    AgentResultConversionError,
)
from .models import AgentAttachmentInput, AgentTaskInput, AgentTaskResult
from .protocols import AgentRuntimeInvocationProtocol


class AgentAdapter:
    """仅转换协议并调用注入端口，不参与规划或任务执行。"""

    def __init__(self, agent_invocation: AgentRuntimeInvocationProtocol) -> None:
        self._agent_invocation = agent_invocation

    def invoke(self, message: UserMessage) -> AgentInvocationResult:
        task = self._to_agent_task(message)
        try:
            result = self._agent_invocation.invoke(task)
        except Exception as exc:
            raise AgentInvocationError("Agent Runtime 调用失败") from exc
        return self._to_gateway_result(result)

    @staticmethod
    def _to_agent_task(message: UserMessage) -> AgentTaskInput:
        if not isinstance(message, UserMessage):
            raise AgentRequestConversionError("message 必须是 Gateway.UserMessage")
        return AgentTaskInput(
            message_id=message.message_id,
            user_id=message.user_id,
            user_task=message.text or "",
            attachments=tuple(AgentAdapter._to_attachment(item) for item in message.attachments),
            metadata=message.metadata,
        )

    @staticmethod
    def _to_attachment(attachment: Attachment) -> AgentAttachmentInput:
        return AgentAttachmentInput(
            attachment_id=attachment.attachment_id,
            reference_id=attachment.reference_id,
            attachment_type=attachment.attachment_type.value,
            file_name=attachment.file_name,
            media_type=attachment.media_type,
            size=attachment.size,
            checksum=attachment.checksum,
            metadata=attachment.metadata,
        )

    @staticmethod
    def _to_gateway_result(result: AgentTaskResult) -> AgentInvocationResult:
        if not isinstance(result, AgentTaskResult):
            raise AgentResultConversionError("Agent Runtime 返回类型无效")
        return AgentInvocationResult(
            task_id=result.task_id,
            status=result.status,
            message=result.message,
            artifacts=result.artifacts,
            metadata=result.metadata,
        )
