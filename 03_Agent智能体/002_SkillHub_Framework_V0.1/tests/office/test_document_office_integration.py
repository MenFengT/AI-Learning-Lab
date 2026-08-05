import unittest

from app.artifact import ArtifactService
from app.core.context import TaskContext
from app.services.office import OfficeService
from app.skills.document import DocumentRequest, DocumentSkill, DocumentType
from app.skills.document.protocols import OfficeServiceProtocol as LegacyProtocol
from app.services.office.protocols import OfficeServiceProtocol

from tests.document.test_document_skill import (
    FakeContentService,
    FixedIdFactory,
    NoFileSystemCalls,
    invocation,
)
from .helpers import mcp_response, policies


class Governance:
    def execute(self, request, context, policy):
        return mcp_response()


class DocumentOfficeIntegrationTests(unittest.TestCase):
    def test_document_skill_calls_real_office_service_boundary(self) -> None:
        self.assertIs(LegacyProtocol, OfficeServiceProtocol)
        office = OfficeService(Governance(), policies())
        artifacts = ArtifactService(NoFileSystemCalls(), FixedIdFactory())
        skill = DocumentSkill(
            FakeContentService(), artifacts, office
        )

        artifact_id = skill.execute(
            TaskContext(
                user_task="生成报告",
                metadata={
                    "document_request": DocumentRequest(
                        DocumentType.REPORT,
                        "集成报告",
                        "result.docx",
                        "验证Office Service边界",
                    )
                },
                invocation_context=invocation(),
            )
        )

        self.assertEqual(artifact_id, "artifact-document-001")


if __name__ == "__main__":
    unittest.main()
