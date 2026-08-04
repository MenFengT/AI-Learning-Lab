import tempfile
import unittest
from pathlib import Path

from app.knowledge import KnowledgeRouter
from app.mcp_servers.filesystem import FileSystemMCPServerAdapter, FileSystemTools
from app.mcp_servers.filesystem import WorkspacePolicy as FileWorkspacePolicy
from app.mcp_servers.knowledge import KnowledgeMCPServerAdapter
from app.mcp_servers.permissions import InMemoryMCPServerPermissionPolicy

from tests.knowledge.test_knowledge_router import build_roots


SKILL_ID = "local/unprivileged@0.2.0"


def payload(tool_name: str, arguments: dict[str, object]) -> dict[str, object]:
    return {
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
            "_meta": {
                "task_id": "task-security",
                "trace_id": "trace-security",
                "span_id": "span-security",
                "skill_id": SKILL_ID,
            },
        },
    }


class MCPServerPermissionBoundaryTests(unittest.TestCase):
    def test_filesystem_adapter_rejects_missing_read_and_write_permissions(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = FileSystemTools(
                FileWorkspacePolicy(root), max_file_size=1024
            )
            adapter = FileSystemMCPServerAdapter(
                tools,
                InMemoryMCPServerPermissionPolicy(
                    {SKILL_ID: frozenset()}
                ),
            )
            read = adapter.handle(
                payload("filesystem.read", {"source": "input/a.txt"})
            )
            write = adapter.handle(
                payload(
                    "filesystem.write",
                    {"target": "output/a.txt", "content": b"data"},
                )
            )

        self.assertEqual(
            read["error_code"], "SHF-SVC-FILE-PERMISSION_DENIED"
        )
        self.assertEqual(
            write["error_code"], "SHF-SVC-FILE-PERMISSION_DENIED"
        )

    def test_knowledge_adapter_rejects_missing_knowledge_permissions(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            domain, standards = build_roots(Path(directory))
            adapter = KnowledgeMCPServerAdapter(
                KnowledgeRouter(domain, standards),
                InMemoryMCPServerPermissionPolicy(
                    {SKILL_ID: frozenset()}
                ),
            )
            query = adapter.handle(
                payload("knowledge.query", {"query_text": "混凝土"})
            )
            standard = adapter.handle(
                payload(
                    "knowledge.get_metadata",
                    {"document_id": "standard.concrete"},
                )
            )

        self.assertEqual(
            query["error_code"], "SHF-MCP-AUTH-PERMISSION_DENIED"
        )
        self.assertEqual(
            standard["error_code"], "SHF-MCP-AUTH-PERMISSION_DENIED"
        )


if __name__ == "__main__":
    unittest.main()
