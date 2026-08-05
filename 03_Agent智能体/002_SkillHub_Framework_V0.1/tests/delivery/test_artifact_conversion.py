from app.delivery import (
    ArtifactDeliveryService,
    DeliveryRequest,
    DeliveryStatus,
)

from .helpers import AllowPolicy, FakeCatalog, FakeTransport, runtime_context, target


def test_artifact_reference_is_converted_to_delivery_result() -> None:
    transport = FakeTransport()
    service = ArtifactDeliveryService(FakeCatalog(), transport, AllowPolicy())

    result = service.deliver(
        DeliveryRequest("artifact-001", "task-001", runtime_context(), target())
    )

    assert result.delivery_id == "delivery-001"
    assert result.artifact_id == "artifact-001"
    assert result.external_reference == "telegram-message-100"
    assert result.status is DeliveryStatus.DELIVERED
    assert result.metadata["artifact_version"] == 2
    assert transport.calls[0][0].name == "报告.docx"
