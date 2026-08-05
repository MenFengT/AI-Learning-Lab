from app.delivery import (
    ArtifactDeliveryReference,
    DeliveryReference,
    DeliveryTarget,
    DeliveryTargetType,
)
from app.runtime.invocation_context import InvocationContext


def runtime_context() -> InvocationContext:
    return InvocationContext(
        task_id="task-001",
        trace_id="trace-001",
        span_id="span-001",
        skill_id="local/document_automation@0.3.0",
        user_id="user-001",
    )


def target() -> DeliveryTarget:
    return DeliveryTarget(DeliveryTargetType.TELEGRAM, "chat-001")


class FakeCatalog:
    def __init__(self, task_id: str = "task-001") -> None:
        self.reference = ArtifactDeliveryReference(
            artifact_id="artifact-001",
            task_id=task_id,
            version=2,
            name="报告.docx",
        )
        self.calls = []

    def get_reference(self, artifact_id, context):
        self.calls.append((artifact_id, context))
        return self.reference


class FakeTransport:
    def __init__(self) -> None:
        self.calls = []

    def deliver(self, artifact, delivery_target, context):
        self.calls.append((artifact, delivery_target, context))
        return DeliveryReference(
            delivery_id="delivery-001",
            artifact_id=artifact.artifact_id,
            external_reference="telegram-message-100",
            target_type=delivery_target.target_type,
        )


class AllowPolicy:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.calls = []

    def allows(self, artifact, delivery_target, context):
        self.calls.append((artifact, delivery_target, context))
        return self.allowed
