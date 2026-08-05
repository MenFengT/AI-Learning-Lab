from app.mcp_servers.office import OfficeMCPServerAdapter
from app.mcp_servers.office.runtime import OfficeCLIAdapter
from app.mcp_servers.permissions import InMemoryMCPServerPermissionPolicy

from .helpers import FakeOfficeRuntime, RecordingAudit, context


def test_mcp_tool_calls_office_cli_adapter() -> None:
    runtime = FakeOfficeRuntime()
    adapter = OfficeCLIAdapter(runtime, RecordingAudit())
    server = OfficeMCPServerAdapter(
        adapter,
        InMemoryMCPServerPermissionPolicy(
            {"local/document_automation@0.3.0": frozenset({"OFFICE_DOCUMENT_CREATE"})}
        ),
    )

    response = server.handle(
        {
            "method": "tools/call",
            "params": {
                "name": "office.create_document",
                "arguments": {"output_name": "result.docx", "content": {"title": "报告"}},
                "_meta": context(),
            },
        }
    )

    assert response["content"]["file"]["file_id"] == "file-office-cli-001"
    assert len(runtime.calls) == 1
    assert runtime.calls[0].operation == "create_document"
