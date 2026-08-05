from app.delivery import ArtifactDeliveryService, DeliveryRequest

from .helpers import AllowPolicy, FakeCatalog, FakeTransport, runtime_context, target


def test_runtime_context_is_passed_unchanged() -> None:
    context = runtime_context()
    catalog = FakeCatalog()
    transport = FakeTransport()
    policy = AllowPolicy()

    ArtifactDeliveryService(catalog, transport, policy).deliver(
        DeliveryRequest("artifact-001", "task-001", context, target())
    )

    assert catalog.calls[0][1] is context
    assert policy.calls[0][2] is context
    assert transport.calls[0][2] is context
    assert context.trace_id == "trace-001"
    assert context.span_id == "span-001"
    assert context.skill_id == "local/document_automation@0.3.0"
