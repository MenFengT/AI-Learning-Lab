import unittest

from app.services.audit import InMemoryAuditService
from app.services.content import ContentService, ContentServiceRequest

from .helpers import Clock, Generator, Knowledge, Planner, runtime_context


class ContentAuditTests(unittest.TestCase):
    def test_success_and_failure_audit_events(self) -> None:
        audit = InMemoryAuditService()
        service = ContentService(Planner(), Knowledge(), Generator(), audit, Clock())
        service.generate_content(
            ContentServiceRequest(
                runtime_context(), "report", "报告", "生成", knowledge_query="事实"
            )
        )
        self.assertEqual(
            [event.metadata["event_type"] for event in audit.events()],
            ["CONTENT_GENERATION_STARTED", "CONTENT_GENERATION_SUCCEEDED"],
        )
        for event in audit.events():
            self.assertEqual(event.task_id, "task-content-001")
            self.assertEqual(event.trace_id, "trace-content-001")
            self.assertEqual(event.skill_id, "local/document_automation@0.4.0")
            self.assertEqual(event.server, "content-service")
            self.assertEqual(event.tool, "content.generate")

        failed_audit = InMemoryAuditService()
        failed = ContentService(
            Planner(), Knowledge(success=False), Generator(), failed_audit, Clock()
        )
        failed.generate_content(
            ContentServiceRequest(
                runtime_context(), "report", "报告", "生成", knowledge_query="事实"
            )
        )
        self.assertEqual(
            [event.metadata["event_type"] for event in failed_audit.events()],
            ["CONTENT_GENERATION_STARTED", "CONTENT_GENERATION_FAILED"],
        )


if __name__ == "__main__":
    unittest.main()
