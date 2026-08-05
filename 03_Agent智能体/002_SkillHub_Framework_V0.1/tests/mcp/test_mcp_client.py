import unittest

from app.services import MCPRequest
from app.services.mcp import (
    ConnectionManager,
    FakeTransport,
    LegacyServerConfigCatalogAdapter,
    MCPClient,
    MCPTransportConnectionError,
    MCPTransportTimeoutError,
    ServerConfig,
)


class FakeRuntimeContext:
    task_id = "task-001"
    trace_id = "trace-001"
    span_id = "span-001"
    skill_id = "local/material_plan@0.2.0"


def server_config(*, enabled: bool = True) -> ServerConfig:
    return ServerConfig(
        server_name="office-server",
        transport_name="fake",
        allowed_tools=frozenset({"office.read_document"}),
        connect_timeout=2.0,
        max_request_timeout=10.0,
        enabled=enabled,
    )


def request(
    *, tool_name: str = "office.read_document", timeout: float = 5.0
) -> MCPRequest:
    return MCPRequest(
        server_name="office-server",
        tool_name=tool_name,
        arguments={"path": "document.docx"},
        runtime_context=FakeRuntimeContext(),
        timeout=timeout,
    )


def build_client(
    transport: FakeTransport,
    *,
    config: ServerConfig | None = None,
) -> MCPClient:
    manager = ConnectionManager({"fake": lambda: transport})
    resolved_config = config or server_config()
    catalog = LegacyServerConfigCatalogAdapter(
        {resolved_config.server_name: resolved_config}
    )
    return MCPClient(catalog, catalog, manager, clock=lambda: 1.0)


class MCPClientTests(unittest.TestCase):
    def test_request_conversion_transport_call_and_context_propagation(self) -> None:
        transport = FakeTransport({"content": {"text": "ok"}})
        response = build_client(transport).call(request())

        self.assertTrue(response.success)
        self.assertEqual(response.content, {"text": "ok"})
        self.assertEqual(response.trace_id, "trace-001")
        self.assertEqual(response.span_id, "span-001")
        self.assertEqual(response.metadata["task_id"], "task-001")
        self.assertEqual(
            response.metadata["skill_id"], "local/material_plan@0.2.0"
        )
        self.assertEqual(transport.send_count, 1)
        self.assertEqual(transport.last_payload["method"], "tools/call")
        self.assertEqual(
            transport.last_payload["params"]["_meta"],
            {
                "task_id": "task-001",
                "trace_id": "trace-001",
                "span_id": "span-001",
                "skill_id": "local/material_plan@0.2.0",
            },
        )

    def test_mcp_error_response_is_converted(self) -> None:
        transport = FakeTransport(
            {
                "is_error": True,
                "error_code": "SHF-MCP-TOOL-NOT_FOUND",
                "message": "Tool不存在",
            }
        )
        response = build_client(transport).call(request())

        self.assertFalse(response.success)
        self.assertEqual(response.error_code, "SHF-MCP-TOOL-NOT_FOUND")
        self.assertEqual(response.attempts, 1)

    def test_timeout_is_passed_and_mapped_without_retry(self) -> None:
        transport = FakeTransport(error=MCPTransportTimeoutError("timeout"))
        response = build_client(transport).call(request(timeout=4.0))

        self.assertFalse(response.success)
        self.assertEqual(response.error_code, "SHF-MCP-CLIENT-TIMEOUT")
        self.assertEqual(transport.last_timeout, 4.0)
        self.assertEqual(transport.send_count, 1)
        self.assertEqual(response.attempts, 1)

    def test_connection_error_is_mapped(self) -> None:
        transport = FakeTransport(
            error=MCPTransportConnectionError("unavailable")
        )
        response = build_client(transport).call(request())

        self.assertEqual(response.error_code, "SHF-MCP-CLIENT-CONNECTION")
        self.assertEqual(transport.send_count, 1)

    def test_tool_whitelist_and_timeout_limit_are_enforced(self) -> None:
        transport = FakeTransport({"content": None})
        client = build_client(transport)

        tool_response = client.call(
            request(tool_name="office.delete_document")
        )
        timeout_response = client.call(request(timeout=11.0))
        self.assertEqual(
            tool_response.error_code,
            "SHF-MCP-REGISTRY-TOOL_NOT_ALLOWED",
        )
        self.assertEqual(
            timeout_response.error_code,
            "SHF-MCP-REGISTRY-TRANSPORT_INVALID",
        )
        self.assertEqual(transport.connect_count, 0)
        self.assertEqual(transport.send_count, 0)

    def test_missing_or_disabled_server_is_rejected(self) -> None:
        transport = FakeTransport({"content": None})
        manager = ConnectionManager({"fake": lambda: transport})
        missing_catalog = LegacyServerConfigCatalogAdapter({})
        missing_client = MCPClient(
            missing_catalog, missing_catalog, manager
        )
        missing_response = missing_client.call(request())
        self.assertEqual(
            missing_response.error_code,
            "SHF-MCP-REGISTRY-SERVER_NOT_FOUND",
        )

        disabled_client = build_client(
            transport, config=server_config(enabled=False)
        )
        disabled_response = disabled_client.call(request())
        self.assertEqual(
            disabled_response.error_code,
            "SHF-MCP-REGISTRY-SERVER_UNHEALTHY",
        )


if __name__ == "__main__":
    unittest.main()
