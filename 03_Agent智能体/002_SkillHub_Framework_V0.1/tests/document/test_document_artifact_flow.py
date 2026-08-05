import unittest

from app.artifact import ArtifactService, ArtifactStatus
from app.core.context import TaskContext
from app.skills.document import DocumentRequest, DocumentSkill, DocumentType

from .test_document_skill import (
    FakeContentService,
    FakeOfficeService,
    FixedIdFactory,
    NoFileSystemCalls,
    file_reference,
    invocation,
)


class RecordingArtifactService(ArtifactService):
    def __init__(self) -> None:
        super().__init__(NoFileSystemCalls(), FixedIdFactory())
        self.statuses: list[ArtifactStatus] = []

    def transition(self, context, artifact_id, status):
        self.statuses.append(status)
        return super().transition(context, artifact_id, status)


class DocumentArtifactFlowTests(unittest.TestCase):
    def test_artifact_moves_from_created_to_processing_to_completed(self) -> None:
        artifacts = RecordingArtifactService()
        skill = DocumentSkill(
            FakeContentService(),
            artifacts,
            FakeOfficeService(file_reference()),
        )
        artifact_id = skill.execute(
            TaskContext(
                user_task="生成报告",
                metadata={
                    "document_request": DocumentRequest(
                        DocumentType.REPORT,
                        "月度报告",
                        "报告.docx",
                        "总结本月情况",
                    )
                },
                invocation_context=invocation(),
            )
        )

        self.assertEqual(
            artifacts.statuses,
            [ArtifactStatus.PROCESSING, ArtifactStatus.COMPLETED],
        )
        self.assertEqual(
            artifacts.get(invocation(), artifact_id).status,
            ArtifactStatus.COMPLETED,
        )


if __name__ == "__main__":
    unittest.main()
