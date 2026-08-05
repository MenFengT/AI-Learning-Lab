"""执行地下室防水施工方案业务闭环。"""

from app.artifact.models import ArtifactStatus, ArtifactType
from app.core.context import TaskContext
from app.runtime.invocation_context import InvocationContext
from app.services.office.models import OfficeDocumentRequest
from app.skills.construction import ConstructionDocumentRequest

from .bootstrap import (
    CONSTRUCTION_SKILL_ID,
    ConstructionDemoApplication,
    create_construction_demo_application,
)
from .models import ConstructionDemoResult
from .request import create_basement_waterproofing_request


def run_construction_demo(
    request: ConstructionDocumentRequest | None = None,
    *,
    application: ConstructionDemoApplication | None = None,
) -> ConstructionDemoResult:
    application = application or create_construction_demo_application()
    request = request or create_basement_waterproofing_request()
    context = InvocationContext(
        task_id="task-construction-demo-001",
        trace_id="trace-construction-demo-001",
        span_id="span-construction-demo-001",
        skill_id=CONSTRUCTION_SKILL_ID,
        user_id="construction-demo-user",
        metadata={"demo": "construction-document-v0.1"},
    )

    generated_content = application.skill.execute(
        TaskContext(
            user_task=request.requirements,
            metadata={"construction_request": request},
            invocation_context=context,
        )
    )
    office_result = application.office_service.create_document(
        OfficeDocumentRequest(
            runtime_context=context,
            output_name="地下室防水施工方案.docx",
            content={
                "title": request.title,
                "body": generated_content,
                "construction_part": request.metadata.get(
                    "construction_part"
                ),
            },
            idempotency_key=f"{context.task_id}:construction-document",
            metadata={"project_name": request.project_name},
        )
    )
    if not office_result.success or office_result.data is None:
        raise RuntimeError(office_result.error_code or "Office文档生成失败")

    artifact = application.artifact_service.create(
        context,
        ArtifactType.DOCUMENT,
        "地下室防水施工方案.docx",
        office_result.data.file_reference,
        {
            "project_name": request.project_name,
            "construction_part": request.metadata.get("construction_part"),
            "document_type": request.document_type.value,
        },
    )
    application.artifact_service.transition(
        context,
        artifact.artifact_id,
        ArtifactStatus.PROCESSING,
    )
    artifact = application.artifact_service.transition(
        context,
        artifact.artifact_id,
        ArtifactStatus.COMPLETED,
    )
    return ConstructionDemoResult(
        artifact=artifact,
        runtime_context=context,
        knowledge_document_ids=(
            application.knowledge_service.document_ids
        ),
        generated_content=generated_content,
        audit_events=application.audit_service.events(),
    )


if __name__ == "__main__":
    print(run_construction_demo())
