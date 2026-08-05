import unittest

from app.mcp_servers.office import OfficeMCPServerAdapter
from app.mcp_servers.permissions import InMemoryMCPServerPermissionPolicy


class RecordingOfficeCLI:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, object]] = []

    def create_document(self, arguments, context):
        self.calls.append(("create", arguments, context))
        return {"file": {}, "format": "docx"}

    def update_document(self, arguments, context):
        self.calls.append(("update", arguments, context))
        return {"file": {}, "format": "docx"}

    def convert_document(self, arguments, context):
        self.calls.append(("convert", arguments, context))
        return {"file": {}, "format": "pdf"}

    def export_document(self, arguments, context):
        self.calls.append(("export", arguments, context))
        return {"file": {}, "format": "pdf"}


def payload(tool: str, arguments=None):
    return {
        "method": "tools/call",
        "params": {
            "name": tool,
            "arguments": arguments or {"output_name": "result.docx"},
            "_meta": {
                "task_id": "task-office-001",
                "trace_id": "trace-office-001",
                "span_id": "span-office-001",
                "skill_id": "local/document_automation@0.3.0",
            },
        },
    }


class OfficeMCPContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cli = RecordingOfficeCLI()
        permissions = frozenset(
            definition.permission
            for definition in OfficeMCPServerAdapter.TOOL_DEFINITIONS
        )
        self.adapter = OfficeMCPServerAdapter(
            self.cli,
            InMemoryMCPServerPermissionPolicy(
                {"local/document_automation@0.3.0": permissions}
            ),
        )

    def test_fixed_tools_have_explicit_contracts_and_no_execute(self) -> None:
        self.assertEqual(
            OfficeMCPServerAdapter.ALLOWED_TOOLS,
            {
                "office.create_document",
                "office.update_document",
                "office.convert_document",
                "office.export_document",
            },
        )
        self.assertNotIn("office.execute", OfficeMCPServerAdapter.ALLOWED_TOOLS)
        for definition in OfficeMCPServerAdapter.TOOL_DEFINITIONS:
            self.assertTrue(definition.input_schema)
            self.assertTrue(definition.output_schema)
            self.assertTrue(definition.permission)

    def test_adapter_passes_complete_runtime_context_to_cli_port(self) -> None:
        result = self.adapter.handle(payload("office.create_document"))

        self.assertNotIn("is_error", result)
        _, _, context = self.cli.calls[0]
        for field in ("task_id", "trace_id", "span_id", "skill_id"):
            self.assertTrue(context[field])

    def test_permission_and_direct_path_inputs_are_rejected(self) -> None:
        denied = OfficeMCPServerAdapter(self.cli).handle(
            payload("office.create_document")
        )
        self.assertEqual(
            denied["error_code"], "SHF-OFFICE-AUTH-PERMISSION_DENIED"
        )
        invalid = self.adapter.handle(
            payload("office.create_document", {"path": "C:/secret.docx"})
        )
        self.assertEqual(
            invalid["error_code"], "SHF-OFFICE-REQUEST-INVALID"
        )
        self.assertEqual(len(self.cli.calls), 0)


if __name__ == "__main__":
    unittest.main()
