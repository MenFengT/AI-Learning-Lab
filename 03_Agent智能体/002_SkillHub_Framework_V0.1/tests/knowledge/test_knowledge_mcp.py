import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

from app.knowledge import KnowledgeRouter
from app.mcp_servers.knowledge import KnowledgeMCPServerAdapter
from app.mcp_servers.permissions import InMemoryMCPServerPermissionPolicy
from app.services.mcp import (
    ConnectionManager,
    LegacyServerConfigCatalogAdapter,
    MCPClient,
    ServerConfig,
)

from .test_knowledge_router import build_roots


class AdapterTransport:
    def __init__(self, adapter: KnowledgeMCPServerAdapter) -> None:
        self.adapter = adapter
        self.connected = False
        self.closed = False
        self.last_payload: Mapping[str, Any] | None = None

    def connect(self, config: ServerConfig) -> None:
        self.connected = True

    def send(
        self, payload: Mapping[str, Any], timeout: float
    ) -> Mapping[str, Any]:
        self.last_payload = payload
        return self.adapter.handle(payload)

    def close(self) -> None:
        self.closed = True
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected


def build_client(
    domain: Path, standards: Path
) -> tuple[MCPClient, AdapterTransport]:
    adapter = KnowledgeMCPServerAdapter(
        KnowledgeRouter(domain, standards),
        InMemoryMCPServerPermissionPolicy(
            {
                "local/material_plan@0.2.0": frozenset(
                    {
                        "KNOWLEDGE_READ",
                        "STANDARDS_READ",
                        "KNOWLEDGE_DOCUMENT_READ",
                    }
                )
            }
        ),
    )
    transport = AdapterTransport(adapter)
    manager = ConnectionManager({"adapter": lambda: transport})
    config = ServerConfig(
        server_name="knowledge-server",
        transport_name="adapter",
        allowed_tools=KnowledgeMCPServerAdapter.ALLOWED_TOOLS,
        connect_timeout=1.0,
        max_request_timeout=10.0,
    )
    catalog = LegacyServerConfigCatalogAdapter({"knowledge-server": config})
    return MCPClient(catalog, catalog, manager), transport


class KnowledgeMCPTests(unittest.TestCase):
    def test_fixed_query_tool_and_runtime_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            domain, standards = build_roots(Path(directory))
            client, transport = build_client(domain, standards)
            from app.services import MCPRequest
            from app.services.knowledge import KnowledgeRuntimeContext

            response = client.call(
                MCPRequest(
                    server_name="knowledge-server",
                    tool_name="knowledge.query",
                    arguments={"query_text": "混凝土"},
                    runtime_context=KnowledgeRuntimeContext(
                        "task-001",
                        "trace-001",
                        "span-001",
                        "local/material_plan@0.2.0",
                    ),
                    timeout=5.0,
                )
            )

        self.assertTrue(response.success)
        self.assertEqual(len(response.content["domain_results"]), 1)
        self.assertEqual(len(response.content["standards_results"]), 1)
        self.assertEqual(
            transport.last_payload["params"]["_meta"]["skill_id"],
            "local/material_plan@0.2.0",
        )
        self.assertTrue(transport.closed)

    def test_unknown_tool_and_file_path_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            domain, standards = build_roots(Path(directory))
            adapter = KnowledgeMCPServerAdapter(
                KnowledgeRouter(domain, standards),
                InMemoryMCPServerPermissionPolicy(
                    {
                        "local/demo@0.1.0": frozenset(
                            {
                                "KNOWLEDGE_READ",
                                "STANDARDS_READ",
                                "KNOWLEDGE_DOCUMENT_READ",
                            }
                        )
                    }
                ),
            )
            context = {
                "task_id": "task",
                "trace_id": "trace",
                "span_id": "span",
                "skill_id": "local/demo@0.1.0",
            }
            unknown = adapter.handle(
                {
                    "method": "tools/call",
                    "params": {"name": "knowledge.dynamic", "_meta": context},
                }
            )
            unsafe = adapter.handle(
                {
                    "method": "tools/call",
                    "params": {
                        "name": "knowledge.get_document",
                        "arguments": {
                            "document_id": "domain.concrete",
                            "path": "../outside.md",
                        },
                        "_meta": context,
                    },
                }
            )

        self.assertEqual(unknown["error_code"], "SHF-MCP-TOOL-NOT_FOUND")
        self.assertEqual(unsafe["error_code"], "SHF-KNW-REQUEST-INVALID")


if __name__ == "__main__":
    unittest.main()
