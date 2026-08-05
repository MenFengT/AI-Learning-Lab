import unittest

from app.services.audit import InMemoryAuditService
from app.services.content import (
    ContentService,
    ContentServiceProtocol,
    ContentServiceRequest,
)

from .helpers import Clock, Generator, Knowledge, Planner, runtime_context


class ContentServiceContractTests(unittest.TestCase):
    def test_service_plans_queries_and_generates_structured_draft(self) -> None:
        planner = Planner()
        knowledge = Knowledge()
        generator = Generator()
        service = ContentService(
            planner, knowledge, generator, InMemoryAuditService(), Clock()
        )
        request = ContentServiceRequest(
            runtime_context(),
            "report",
            "月度报告",
            "基于事实生成",
            knowledge_query="月度事实",
        )

        result = service.generate_content(request)

        self.assertIsInstance(service, ContentServiceProtocol)
        self.assertTrue(result.success)
        self.assertEqual(result.data.title, "月度报告")
        self.assertEqual(len(planner.requests), 1)
        self.assertEqual(len(knowledge.requests), 1)
        self.assertEqual(len(generator.calls), 1)

    def test_knowledge_failure_is_standardized(self) -> None:
        service = ContentService(
            Planner(),
            Knowledge(success=False),
            Generator(),
            InMemoryAuditService(),
            Clock(),
        )
        result = service.generate_content(
            ContentServiceRequest(
                runtime_context(), "report", "报告", "生成报告"
            )
        )
        self.assertFalse(result.success)
        self.assertEqual(
            result.error_code, "SHF-CONTENT-KNOWLEDGE-FAILED"
        )


if __name__ == "__main__":
    unittest.main()
