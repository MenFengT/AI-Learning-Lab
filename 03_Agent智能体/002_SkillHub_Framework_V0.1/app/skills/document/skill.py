"""文档自动化业务Skill；基础能力全部经Service协议访问。"""

from typing import Any, Mapping

from app.artifact.models import ArtifactStatus, ArtifactType
from app.artifact.protocols import ArtifactServiceProtocol
from app.core.context import TaskContext
from app.services.content.models import ContentServiceRequest
from app.skills.base_skill import BaseSkill

from .errors import (
    DocumentDependencyError,
    DocumentRequestError,
)
from .models import (
    DocumentRequest,
    DocumentType,
    OfficeDocumentRequest,
)
from .protocols import ContentServiceProtocol, OfficeServiceProtocol


class DocumentSkill(BaseSkill):
    """组织文档业务输入，并协调受控Service生成产物。"""

    name = "document_automation"
    description = "根据结构化需求与知识上下文生成文档产物"
    keywords = ("方案", "报告", "论文", "文档")

    def __init__(
        self,
        content_service: ContentServiceProtocol,
        artifact_service: ArtifactServiceProtocol,
        office_service: OfficeServiceProtocol,
    ) -> None:
        self._content_service = content_service
        self._artifact_service = artifact_service
        self._office_service = office_service

    def execute(self, context: TaskContext) -> str:
        invocation = context.invocation_context
        if invocation is None:
            raise DocumentRequestError("DocumentSkill需要InvocationContext")
        request = context.metadata.get("document_request")
        if request is None:
            step_inputs = context.metadata.get("step_inputs")
            if isinstance(step_inputs, Mapping):
                request = _document_request(step_inputs)
        if not isinstance(request, DocumentRequest):
            raise DocumentRequestError(
                "TaskContext.metadata.document_request必须为DocumentRequest"
            )

        content_result = self._content_service.generate_content(
            ContentServiceRequest(
                runtime_context=invocation,
                document_type=request.document_type.value,
                title=request.title,
                requirements=request.requirements,
                requested_sections=request.sections,
                knowledge_query=request.knowledge_query,
                metadata=request.metadata,
            )
        )
        if not content_result.success or content_result.data is None:
            raise DocumentDependencyError(
                content_result.error_code or "ContentService生成内容失败"
            )
        draft = content_result.data
        office_result = self._office_service.create_document(
            OfficeDocumentRequest(
                runtime_context=invocation,
                output_name=request.output_name,
                content={
                    "title": draft.title,
                    "sections": draft.sections,
                    "paragraphs": tuple(
                        {
                            "section_id": paragraph.section_id,
                            "order": paragraph.order,
                            "text": paragraph.text,
                        }
                        for paragraph in draft.paragraphs
                    ),
                    "metadata": dict(draft.metadata),
                },
                metadata={"document_type": request.document_type.value},
            )
        )
        if not office_result.success or office_result.data is None:
            raise DocumentDependencyError(
                office_result.error_code or "OfficeService创建文档失败"
            )

        artifact = self._artifact_service.create(
            invocation,
            ArtifactType.DOCUMENT,
            request.output_name,
            office_result.data.file_reference,  # type: ignore[arg-type]
            {
                "document_type": request.document_type.value,
                "title": request.title,
            },
        )
        self._artifact_service.transition(
            invocation, artifact.artifact_id, ArtifactStatus.PROCESSING
        )
        completed = self._artifact_service.transition(
            invocation, artifact.artifact_id, ArtifactStatus.COMPLETED
        )
        return completed.artifact_id


def _document_request(value: Mapping[str, Any]) -> DocumentRequest:
    try:
        metadata = value.get("metadata", {})
        return DocumentRequest(
            document_type=DocumentType(str(value["document_type"])),
            title=str(value["title"]),
            output_name=str(value["output_name"]),
            requirements=str(value["requirements"]),
            sections=tuple(str(item) for item in value.get("sections", ())),
            knowledge_query=(
                str(value["knowledge_query"])
                if value.get("knowledge_query") is not None
                else None
            ),
            metadata=metadata if isinstance(metadata, Mapping) else {},
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DocumentRequestError("PlanStep文档输入无效") from exc
