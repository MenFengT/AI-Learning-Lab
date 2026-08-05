import unittest

from app.services.audit import InMemoryAuditService
from app.services.governance import GovernanceConfig, ServiceCallExecutor
from app.services.office import OfficeService

from .helpers import mcp_response, office_request, policies


class Clock:
    def now(self):
        return 0.0


class MCPClient:
    def __init__(self, success=True):
        self.success = success

    def call(self, request):
        return mcp_response(success=self.success)


class Retry:
    def execute(self, operation, policy, *, timeout_seconds):
        return operation()


class Circuit:
    def allow_request(self, key):
        return None

    def record_success(self, key):
        return None

    def record_failure(self, key):
        return None


class OfficeAuditTests(unittest.TestCase):
    def build(self, success=True):
        audit = InMemoryAuditService()
        executor = ServiceCallExecutor(
            MCPClient(success), audit, Retry(), Circuit(), Clock(), GovernanceConfig()
        )
        return OfficeService(executor, policies()), audit

    def test_success_and_failure_audit_lifecycle(self) -> None:
        service, audit = self.build(True)
        service.create_document(office_request())
        self.assertEqual(
            [event.metadata["event_type"] for event in audit.events()],
            ["SERVICE_CALL_STARTED", "SERVICE_CALL_SUCCEEDED"],
        )
        for event in audit.events():
            self.assertEqual(event.task_id, "task-office-001")
            self.assertEqual(event.trace_id, "trace-office-001")
            self.assertEqual(event.skill_id, "local/document_automation@0.3.0")
            self.assertEqual(event.server, "office-server")
            self.assertEqual(event.tool, "office.create_document")

        failed_service, failed_audit = self.build(False)
        failed_service.create_document(office_request())
        self.assertEqual(
            [event.metadata["event_type"] for event in failed_audit.events()],
            ["SERVICE_CALL_STARTED", "SERVICE_CALL_FAILED"],
        )


if __name__ == "__main__":
    unittest.main()
