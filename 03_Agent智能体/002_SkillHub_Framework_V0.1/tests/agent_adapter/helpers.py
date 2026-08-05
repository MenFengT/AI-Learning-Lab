from app.adapters.agent.models import AgentTaskInput, AgentTaskResult
from app.gateway.models import (
    AgentArtifactReference,
    AsyncTaskStatus,
    Attachment,
    AttachmentType,
    UserMessage,
)


class FakeAgentRuntime:
    def __init__(self, result: AgentTaskResult | None = None) -> None:
        self.calls: list[AgentTaskInput] = []
        self.result = result or AgentTaskResult(
            task_id="task-001",
            status=AsyncTaskStatus.COMPLETED,
            message="完成",
            artifacts=(
                AgentArtifactReference(
                    artifact_id="artifact-001",
                    version=1,
                    artifact_type="DOCUMENT",
                    name="报告.docx",
                ),
            ),
            metadata={"trace_id": "trace-001"},
        )

    def invoke(self, task: AgentTaskInput) -> AgentTaskResult:
        self.calls.append(task)
        return self.result


def make_message() -> UserMessage:
    return UserMessage(
        message_id="message-001",
        user_id="user-001",
        text="生成项目报告",
        attachments=(
            Attachment(
                attachment_id="attachment-001",
                attachment_type=AttachmentType.WORD,
                file_name="source.docx",
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                size=128,
                checksum="a" * 64,
                reference_id="file-001",
                metadata={"source": "telegram"},
            ),
        ),
        metadata={"channel": "telegram"},
    )
