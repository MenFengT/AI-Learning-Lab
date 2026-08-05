import ast
import unittest
from pathlib import Path

from app.artifact import ArtifactService
from app.core.context import TaskContext
from app.skills.document import DocumentRequest, DocumentSkill, DocumentType
from app.skills.document import skill as document_skill_module

from tests.document.test_document_skill import (
    FakeContentService,
    FakeOfficeService,
    FixedIdFactory,
    NoFileSystemCalls,
    file_reference,
    invocation,
)


class DocumentSkillContentIntegrationTests(unittest.TestCase):
    def test_document_skill_calls_content_service_then_office(self) -> None:
        content = FakeContentService()
        office = FakeOfficeService(file_reference())
        skill = DocumentSkill(
            content,
            ArtifactService(NoFileSystemCalls(), FixedIdFactory()),
            office,
        )
        artifact_id = skill.execute(
            TaskContext(
                user_task="生成报告",
                metadata={
                    "document_request": DocumentRequest(
                        DocumentType.REPORT,
                        "集成报告",
                        "result.docx",
                        "验证内容集成",
                    )
                },
                invocation_context=invocation(),
            )
        )
        self.assertEqual(artifact_id, "artifact-document-001")
        self.assertEqual(len(content.requests), 1)
        self.assertEqual(len(office.requests), 1)

    def test_document_skill_does_not_import_content_internals_or_knowledge(self) -> None:
        tree = ast.parse(
            Path(document_skill_module.__file__).read_text(encoding="utf-8")
        )
        imports = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        ]
        forbidden = (
            "app.content.planner",
            "app.content.generator",
            "app.content.templates",
            "app.services.knowledge",
        )
        self.assertFalse(any(name.startswith(forbidden) for name in imports))


if __name__ == "__main__":
    unittest.main()
