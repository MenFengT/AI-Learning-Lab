import ast
import unittest
from pathlib import Path

from app.services.office import OfficeService, OfficeServiceProtocol
from app.services.office import service as office_service_module

from .helpers import mcp_response, office_request, policies


class RecordingGovernanceExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object, object]] = []

    def execute(self, request, context, policy):
        self.calls.append((request, context, policy))
        return mcp_response()


class OfficeServiceTests(unittest.TestCase):
    def test_service_uses_governance_and_preserves_runtime_context(self) -> None:
        executor = RecordingGovernanceExecutor()
        service = OfficeService(executor, policies())

        result = service.create_document(office_request())

        self.assertTrue(result.success)
        self.assertIsInstance(service, OfficeServiceProtocol)
        self.assertEqual(result.data.file_reference.file_id, "file-office-001")
        request, context, _ = executor.calls[0]
        self.assertEqual(request.server_name, "office-server")
        self.assertEqual(request.tool_name, "office.create_document")
        self.assertEqual(request.runtime_context.task_id, "task-office-001")
        self.assertEqual(request.runtime_context.trace_id, "trace-office-001")
        self.assertEqual(request.runtime_context.skill_id, "local/document_automation@0.3.0")
        self.assertNotEqual(request.runtime_context.span_id, "span-skill-001")
        self.assertEqual(context.parent_span_id, "span-skill-001")

    def test_service_has_no_officecli_or_file_operations(self) -> None:
        tree = ast.parse(Path(office_service_module.__file__).read_text(encoding="utf-8"))
        imports = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        ]
        self.assertFalse(any("officecli" in name.casefold() for name in imports))
        forbidden = {"open", "read_file", "write_file", "call_tool"}
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue(forbidden.isdisjoint(calls))


if __name__ == "__main__":
    unittest.main()
