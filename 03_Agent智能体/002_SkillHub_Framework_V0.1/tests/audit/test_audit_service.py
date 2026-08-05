import unittest

from app.services.audit import (
    AuditEvent,
    AuditServiceProtocol,
    InMemoryAuditService,
)


class AuditServiceTests(unittest.TestCase):
    def test_event_is_recorded_as_an_immutable_snapshot(self) -> None:
        metadata = {"attempt": 1, "source": {"pages": [1, 2]}}
        event = AuditEvent(
            task_id="task-001",
            trace_id="trace-001",
            span_id="span-001",
            skill_id="local/material_plan@0.2.0",
            server="office-server",
            tool="read-document",
            duration=12.5,
            error_code=None,
            metadata=metadata,
        )
        metadata["source"]["pages"].append(3)
        service = InMemoryAuditService()

        service.record(event)
        recorded = service.events()[0]

        self.assertIsInstance(service, AuditServiceProtocol)
        self.assertEqual(recorded.task_id, "task-001")
        self.assertEqual(recorded.trace_id, "trace-001")
        self.assertEqual(recorded.span_id, "span-001")
        self.assertEqual(recorded.skill_id, "local/material_plan@0.2.0")
        self.assertEqual(recorded.metadata["source"]["pages"], (1, 2))
        with self.assertRaises(TypeError):
            recorded.metadata["attempt"] = 2

    def test_sensitive_values_and_full_content_are_redacted(self) -> None:
        service = InMemoryAuditService()
        service.record(
            AuditEvent(
                task_id="task-001",
                trace_id="trace-001",
                span_id="span-001",
                skill_id="local/material_plan@0.2.0",
                server="filesystem-server",
                tool="read-file",
                duration=2.0,
                error_code="SHF-MCP-CLIENT-TIMEOUT",
                metadata={
                    "token": "token-value",
                    "password": "password-value",
                    "request": {
                        "file_content": "complete file contents",
                        "path": "safe-name.txt",
                    },
                },
            )
        )

        metadata = service.events()[0].metadata
        self.assertEqual(metadata["token"], "[REDACTED]")
        self.assertEqual(metadata["password"], "[REDACTED]")
        self.assertEqual(
            metadata["request"]["file_content"], "[REDACTED]"
        )
        self.assertEqual(metadata["request"]["path"], "safe-name.txt")


if __name__ == "__main__":
    unittest.main()
