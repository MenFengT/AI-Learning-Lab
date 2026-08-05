from app.artifact.models import ArtifactStatus, ArtifactType
from app.demo.construction_demo import (
    create_basement_waterproofing_request,
    create_construction_demo_application,
    run_construction_demo,
)


def test_basement_waterproofing_real_protocol_workflow() -> None:
    application = create_construction_demo_application()
    result = run_construction_demo(
        create_basement_waterproofing_request(
            project_name="城市中心项目",
            construction_part="地下室底板、外墙和顶板",
        ),
        application=application,
    )

    assert result.artifact.status is ArtifactStatus.COMPLETED
    assert result.artifact.artifact_type is ArtifactType.DOCUMENT
    assert result.artifact.file_reference.area.value == "output"
    assert result.artifact.name == "地下室防水施工方案.docx"
    assert result.artifact.metadata["project_name"] == "城市中心项目"

    assert "construction.basement_waterproofing.practice" in (
        result.knowledge_document_ids
    )
    assert "construction.scheme.template" in result.knowledge_document_ids
    assert "construction.safety_civilized.requirements" in (
        result.knowledge_document_ids
    )
    assert "地下室防水施工方案" in result.generated_content
    assert application.office_runtime.requests


def test_runtime_context_and_audit_are_complete() -> None:
    application = create_construction_demo_application()
    result = run_construction_demo(application=application)
    context = result.runtime_context

    assert context.task_id
    assert context.trace_id
    assert context.span_id
    assert context.skill_id == "local/construction_document@0.1.0"
    assert all(event.task_id == context.task_id for event in result.audit_events)
    assert all(event.trace_id == context.trace_id for event in result.audit_events)
    assert all(event.skill_id == context.skill_id for event in result.audit_events)
    assert all(event.span_id for event in result.audit_events)

    event_types = {
        str(event.metadata.get("event_type"))
        for event in result.audit_events
    }
    assert "SERVICE_CALL_STARTED" in event_types
    assert "SERVICE_CALL_SUCCEEDED" in event_types
    assert "CONTENT_GENERATION_STARTED" in event_types
    assert "CONTENT_GENERATION_SUCCEEDED" in event_types
    assert not any(event.error_code for event in result.audit_events)
