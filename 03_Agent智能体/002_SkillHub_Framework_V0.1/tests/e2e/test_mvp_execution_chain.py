from app.adapters.telegram import TelegramMessage
from app.demo.demo_bootstrap import DOCUMENT_SKILL_ID, create_demo_application
from app.gateway.models import AsyncTaskStatus
from app.runtime.lifecycle import LifecycleStatus


def test_telegram_document_generation_delivery_closed_loop() -> None:
    application = create_demo_application()

    response = application.container.telegram_adapter.handle(
        TelegramMessage(
            message_id="1",
            chat_id="10001",
            user_id="20001",
            text="生成一份项目开工报告",
        )
    )

    assert response.status is AsyncTaskStatus.COMPLETED
    assert response.message == "项目开工报告已生成并交付"
    assert response.artifacts[0].artifact_type == "DOCUMENT"
    assert response.artifacts[0].name == "项目开工报告.docx"
    assert response.metadata["external_reference"].startswith("telegram://10001/")

    environment = application.container.runtime_manager.get_environment(response.task_id)
    assert environment.lifecycle.status is LifecycleStatus.COMPLETED
    assert response.metadata["trace_id"] == environment.context.trace_id
    assert response.metadata["span_id"]
    assert application.container.skill_registry.get_by_id(DOCUMENT_SKILL_ID).skill_id == DOCUMENT_SKILL_ID


def test_real_protocol_chain_reaches_office_cli_artifact_and_delivery() -> None:
    application = create_demo_application()
    response = application.container.telegram_adapter.handle(
        TelegramMessage("2", "10002", "20002", "生成一份项目开工报告")
    )

    assert len(application.office_cli_runtime.requests) == 1
    office_request = application.office_cli_runtime.requests[0]
    assert office_request.task_id == response.task_id
    assert office_request.trace_id == response.metadata["trace_id"]
    assert office_request.skill_id == DOCUMENT_SKILL_ID
    assert office_request.operation == "create_document"

    assert len(application.delivery_transport.deliveries) == 1
    artifact, target, context = application.delivery_transport.deliveries[0]
    assert artifact.artifact_id == response.artifacts[0].artifact_id
    assert context.task_id == response.task_id
    assert target.recipient_reference == "10002"


def test_content_office_governance_and_cli_audit_events_exist() -> None:
    application = create_demo_application()
    application.container.telegram_adapter.handle(
        TelegramMessage("3", "10003", "20003", "生成一份项目开工报告")
    )

    event_types = {
        event.metadata.get("event_type") for event in application.audit_service.events()
    }
    assert "CONTENT_GENERATION_STARTED" in event_types
    assert "CONTENT_GENERATION_SUCCEEDED" in event_types
    assert "SERVICE_CALL_STARTED" in event_types
    assert "SERVICE_CALL_SUCCEEDED" in event_types
    assert "OFFICE_CLI_STARTED" in event_types
    assert "OFFICE_CLI_SUCCEEDED" in event_types
