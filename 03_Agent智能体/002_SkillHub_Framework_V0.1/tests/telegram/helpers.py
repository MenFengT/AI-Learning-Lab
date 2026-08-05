from app.gateway import (
    AgentArtifactReference,
    AgentResponse,
    AsyncTaskStatus,
    Attachment,
    AttachmentType,
)


class AttachmentResolver:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.attachments: list[object] = []

    def resolve(self, attachment):
        self.attachments.append(attachment)
        if self.fail:
            raise RuntimeError("upload unavailable")
        return Attachment(
            attachment_id=f"telegram-file-{len(self.attachments)}",
            attachment_type=AttachmentType.WORD,
            file_name=attachment.filename,
            media_type=attachment.mime_type,
            size=attachment.size,
            checksum="0123456789abcdef",
            reference_id="telegram-upload-001",
            metadata={"telegram_file_id": attachment.telegram_file_id},
        )


class Gateway:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.messages: list[object] = []

    def handle(self, message):
        self.messages.append(message)
        if self.fail:
            raise RuntimeError("gateway unavailable")
        return AgentResponse(
            task_id="task-telegram-001",
            status=AsyncTaskStatus.COMPLETED,
            message="处理完成",
            artifacts=(
                AgentArtifactReference(
                    "artifact-telegram-001", 1, "DOCUMENT", "result.docx"
                ),
            ),
            metadata={"trace_id": "trace-telegram-001"},
        )
