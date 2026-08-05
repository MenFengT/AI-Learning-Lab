import unittest
from datetime import datetime, timezone

from app.artifact import ArtifactService, ArtifactStatus
from app.content import ContentDraft, ContentParagraph
from app.core.context import TaskContext
from app.runtime.invocation_context import InvocationContext
from app.services.knowledge.models import KnowledgeQueryData
from app.services.models import ServiceResult
from app.services.filesystem.models import (
    FileMetadata,
    FileReference,
    WorkspaceArea,
)
from app.skills.document import DocumentRequest, DocumentSkill, DocumentType
from app.skills.document.models import OfficeDocumentResult


class FixedIdFactory:
    def create(self) -> str:
        return "artifact-document-001"


class NoFileSystemCalls:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"Document流程不得直接执行文件操作：{name}")


class FakeKnowledgeService:
    def __init__(self) -> None:
        self.requests: list[object] = []

    def query(self, request: object) -> ServiceResult[KnowledgeQueryData]:
        self.requests.append(request)
        return ServiceResult(
            success=True,
            data=KnowledgeQueryData((), (), ()),
            error_code=None,
            message="ok",
            trace_id="trace-001",
        )


class FakeContentService:
    def __init__(self) -> None:
        self.requests: list[object] = []

    def generate_content(self, request: object) -> ServiceResult[ContentDraft]:
        self.requests.append(request)
        return ServiceResult(
            success=True,
            data=ContentDraft(
                title=request.title,
                sections=("background", "implementation"),
                paragraphs=(
                    ContentParagraph("background", 1, "背景正文"),
                    ContentParagraph("implementation", 2, "实施正文"),
                ),
            ),
            error_code=None,
            message="generated",
            trace_id="trace-001",
        )


class FakeOfficeService:
    def __init__(self, reference: FileReference) -> None:
        self.reference = reference
        self.requests: list[object] = []

    def create_document(self, request: object) -> ServiceResult[OfficeDocumentResult]:
        self.requests.append(request)
        return ServiceResult(
            success=True,
            data=OfficeDocumentResult(self.reference, "docx"),
            error_code=None,
            message="created",
            trace_id="trace-001",
        )


class FakePromptLoader:
    def __init__(self) -> None:
        self.loaded: list[str] = []

    def load(self, template_name: str) -> str:
        self.loaded.append(template_name)
        return "外置测试模板"


def invocation() -> InvocationContext:
    return InvocationContext(
        task_id="task-document-001",
        trace_id="trace-001",
        span_id="span-001",
        skill_id="local/document_automation@0.3.0",
    )


def file_reference() -> FileReference:
    now = datetime.now(timezone.utc)
    return FileReference(
        file_id="file-document-001",
        version="1",
        checksum="checksum-document-001",
        area=WorkspaceArea.OUTPUT,
        relative_path="task-document-001/result.docx",
        metadata=FileMetadata(
            size=128,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            created_at=now,
            updated_at=now,
        ),
        created_at=now,
        updated_at=now,
    )


class DocumentSkillTests(unittest.TestCase):
    def test_document_request_is_organized_and_services_are_injected(self) -> None:
        content = FakeContentService()
        office = FakeOfficeService(file_reference())
        artifacts = ArtifactService(NoFileSystemCalls(), FixedIdFactory())
        skill = DocumentSkill(content, artifacts, office)
        context = TaskContext(
            user_task="生成项目方案",
            metadata={
                "document_request": DocumentRequest(
                    document_type=DocumentType.PROPOSAL,
                    title="数字化建设方案",
                    output_name="方案.docx",
                    requirements="给出实施路径",
                    sections=("background", "implementation"),
                    knowledge_query="企业数字化标准",
                )
            },
            invocation_context=invocation(),
        )

        artifact_id = skill.execute(context)

        self.assertEqual(artifact_id, "artifact-document-001")
        self.assertEqual(len(content.requests), 1)
        self.assertEqual(content.requests[0].runtime_context, invocation())
        self.assertEqual(len(office.requests), 1)
        office_request = office.requests[0]
        self.assertEqual(office_request.content["title"], "数字化建设方案")
        self.assertEqual(
            [
                paragraph["section_id"]
                for paragraph in office_request.content["paragraphs"]
            ],
            ["background", "implementation"],
        )
        artifact = artifacts.get(invocation(), artifact_id)
        self.assertEqual(artifact.status, ArtifactStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
