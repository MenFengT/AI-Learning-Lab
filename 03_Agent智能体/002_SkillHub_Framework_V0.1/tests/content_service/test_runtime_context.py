import unittest

from app.services.audit import InMemoryAuditService
from app.services.content import ContentService, ContentServiceRequest

from .helpers import Clock, Generator, Knowledge, Planner, runtime_context


class ContentRuntimeContextTests(unittest.TestCase):
    def test_context_flows_to_knowledge_generator_and_result(self) -> None:
        knowledge = Knowledge()
        generator = Generator()
        service = ContentService(
            Planner(), knowledge, generator, InMemoryAuditService(), Clock()
        )
        original = runtime_context()
        result = service.generate_content(
            ContentServiceRequest(
                original, "report", "报告", "生成内容", knowledge_query="事实"
            )
        )

        knowledge_context = knowledge.requests[0].runtime_context
        generation_context = generator.calls[0][1]
        self.assertEqual(knowledge_context.task_id, original.task_id)
        self.assertEqual(knowledge_context.trace_id, original.trace_id)
        self.assertEqual(knowledge_context.skill_id, original.skill_id)
        self.assertNotEqual(knowledge_context.span_id, original.span_id)
        self.assertEqual(
            generation_context.metadata["task_id"], original.task_id
        )
        self.assertEqual(
            generation_context.metadata["trace_id"], original.trace_id
        )
        self.assertEqual(
            generation_context.metadata["span_id"], knowledge_context.span_id
        )
        self.assertEqual(result.trace_id, original.trace_id)
        self.assertEqual(result.metadata["span_id"], knowledge_context.span_id)


if __name__ == "__main__":
    unittest.main()
