import inspect
import unittest

from app.runtime.invocation_context import InvocationContext
from app.services.governance import (
    GovernanceConfig,
    ServiceCallContext,
    ServiceCallExecutor,
)


class GovernanceContextTests(unittest.TestCase):
    def test_context_is_isolated_and_links_parent_span(self) -> None:
        source = {"source": {"pages": [1, 2]}}
        invocation = InvocationContext(
            task_id="task-001",
            trace_id="trace-001",
            span_id="skill-span",
            skill_id="local/demo@0.2.0",
        )

        context = ServiceCallContext(
            runtime_context=invocation,
            service_name="knowledge-service",
            operation_name="query",
            service_span_id="service-span",
            parent_span_id="skill-span",
            request_metadata=source,
        )
        source["source"]["pages"].append(3)

        self.assertEqual(context.parent_span_id, invocation.span_id)
        self.assertEqual(context.request_metadata["source"]["pages"], (1, 2))
        with self.assertRaises(TypeError):
            context.request_metadata["new"] = "value"

    def test_invalid_parent_span_is_rejected(self) -> None:
        invocation = InvocationContext(
            task_id="task-001",
            trace_id="trace-001",
            span_id="skill-span",
            skill_id="local/demo@0.2.0",
        )

        with self.assertRaisesRegex(ValueError, "parent_span_id"):
            ServiceCallContext(
                runtime_context=invocation,
                service_name="knowledge-service",
                operation_name="query",
                service_span_id="service-span",
                parent_span_id="wrong-span",
            )

    def test_executor_requires_all_named_dependencies(self) -> None:
        parameters = inspect.signature(ServiceCallExecutor).parameters

        self.assertEqual(
            tuple(parameters),
            (
                "mcp_client",
                "audit_service",
                "retry_executor",
                "circuit_breaker",
                "clock",
                "config",
            ),
        )
        self.assertFalse(hasattr(ServiceCallExecutor, "get_dependency"))
        self.assertFalse(hasattr(ServiceCallExecutor, "resolve"))
        self.assertEqual(GovernanceConfig().schema_version, "0.1")


if __name__ == "__main__":
    unittest.main()
