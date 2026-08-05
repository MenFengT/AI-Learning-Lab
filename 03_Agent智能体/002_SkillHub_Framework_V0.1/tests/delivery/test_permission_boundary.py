import pytest

from app.delivery import (
    ArtifactDeliveryService,
    DeliveryPermissionError,
    DeliveryRequest,
)

from .helpers import AllowPolicy, FakeCatalog, FakeTransport, runtime_context, target


def test_denied_delivery_never_calls_transport() -> None:
    transport = FakeTransport()
    service = ArtifactDeliveryService(FakeCatalog(), transport, AllowPolicy(False))
    with pytest.raises(DeliveryPermissionError):
        service.deliver(
            DeliveryRequest("artifact-001", "task-001", runtime_context(), target())
        )
    assert transport.calls == []


def test_cross_task_artifact_is_rejected() -> None:
    transport = FakeTransport()
    service = ArtifactDeliveryService(
        FakeCatalog(task_id="task-other"), transport, AllowPolicy()
    )
    with pytest.raises(DeliveryPermissionError):
        service.deliver(
            DeliveryRequest("artifact-001", "task-001", runtime_context(), target())
        )
    assert transport.calls == []
