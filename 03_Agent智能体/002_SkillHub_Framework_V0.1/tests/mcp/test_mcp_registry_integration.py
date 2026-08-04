import inspect
import unittest

from app.mcp_registry import (
    MCPServerCatalogProtocol,
    MCPServerDescriptor,
    MCPServerRegistry,
    ServerCapabilities,
    ServerHealthStatus,
    ToolDescriptor,
    ToolIdempotency,
    TransportType,
    build_server_id,
)
from app.services import MCPRequest
from app.services.mcp import (
    ConnectionManager,
    FakeTransport,
    LegacyServerConfigCatalogAdapter,
    MCPClient,
    ServerConfig,
    TransportConfigProviderProtocol,
)


class RuntimeContext:
    task_id = "task-registry"
    trace_id = "trace-registry"
    span_id = "span-registry"
    skill_id = "local/registry_test@0.2.0"


class RecordingTransportConfigProvider:
    def __init__(self, config: ServerConfig | None) -> None:
        self.config = config
        self.references: list[str] = []

    def resolve(self, transport_config_reference: str) -> ServerConfig:
        self.references.append(transport_config_reference)
        if self.config is None:
            raise KeyError(transport_config_reference)
        return self.config


def descriptor(
    *, health: ServerHealthStatus = ServerHealthStatus.HEALTHY
) -> MCPServerDescriptor:
    return MCPServerDescriptor(
        server_id=build_server_id("office-server", "0.2.0"),
        server_name="office-server",
        version="0.2.0",
        description="Office test server",
        transport_type=TransportType.IN_MEMORY,
        transport_config_reference="mcp.office.v0_2",
        capabilities=ServerCapabilities(tools=True),
        allowed_tools=(
            ToolDescriptor(
                tool_name="office.read",
                description="Read a document",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                permission_required="OFFICE_READ",
                idempotency=ToolIdempotency.IDEMPOTENT,
            ),
        ),
        health_status=health,
    )


def config() -> ServerConfig:
    return ServerConfig(
        server_name="office-server",
        transport_name="fake",
        allowed_tools=frozenset({"office.read"}),
        connect_timeout=1.0,
        max_request_timeout=10.0,
    )


def request(*, server_name: str = "office-server", tool_name: str = "office.read") -> MCPRequest:
    return MCPRequest(
        server_name=server_name,
        tool_name=tool_name,
        arguments={"document_id": "doc-001"},
        runtime_context=RuntimeContext(),
        timeout=5.0,
    )


def build_client(
    registry: MCPServerRegistry,
    provider: RecordingTransportConfigProvider,
    transport: FakeTransport,
) -> MCPClient:
    return MCPClient(
        registry,
        provider,
        ConnectionManager({"fake": lambda: transport}),
    )


class MCPRegistryIntegrationTests(unittest.TestCase):
    def test_legacy_adapter_exposes_catalog_and_config_provider_contracts(
        self,
    ) -> None:
        legacy_config = config()
        adapter = LegacyServerConfigCatalogAdapter(
            {legacy_config.server_name: legacy_config}
        )

        self.assertIsInstance(adapter, MCPServerCatalogProtocol)
        self.assertIsInstance(adapter, TransportConfigProviderProtocol)
        server = adapter.get("office-server")
        self.assertEqual(server.tool("office.read").tool_name, "office.read")
        self.assertIs(
            adapter.resolve(server.transport_config_reference), legacy_config
        )

    def test_registry_provider_transport_and_runtime_context(self) -> None:
        registry = MCPServerRegistry()
        registry.register(descriptor())
        provider = RecordingTransportConfigProvider(config())
        transport = FakeTransport({"content": {"ok": True}})

        response = build_client(registry, provider, transport).call(request())

        self.assertTrue(response.success)
        self.assertEqual(provider.references, ["mcp.office.v0_2"])
        self.assertEqual(
            transport.last_payload["params"]["_meta"],
            {
                "task_id": "task-registry",
                "trace_id": "trace-registry",
                "span_id": "span-registry",
                "skill_id": "local/registry_test@0.2.0",
            },
        )

    def test_registry_rejections_do_not_resolve_or_connect(self) -> None:
        cases = (
            (
                MCPServerRegistry(),
                request(),
                "SHF-MCP-REGISTRY-SERVER_NOT_FOUND",
            ),
            (
                self._registry(descriptor()),
                request(tool_name="office.delete"),
                "SHF-MCP-REGISTRY-TOOL_NOT_ALLOWED",
            ),
            (
                self._registry(
                    descriptor(health=ServerHealthStatus.UNHEALTHY)
                ),
                request(),
                "SHF-MCP-REGISTRY-SERVER_UNHEALTHY",
            ),
        )
        for registry, mcp_request, expected_code in cases:
            with self.subTest(error_code=expected_code):
                provider = RecordingTransportConfigProvider(config())
                transport = FakeTransport({"content": None})
                response = build_client(
                    registry, provider, transport
                ).call(mcp_request)
                self.assertEqual(response.error_code, expected_code)
                self.assertEqual(provider.references, [])
                self.assertEqual(transport.connect_count, 0)

    def test_invalid_transport_reference_mapping_is_stable(self) -> None:
        registry = self._registry(descriptor())
        provider = RecordingTransportConfigProvider(None)
        transport = FakeTransport({"content": None})

        response = build_client(registry, provider, transport).call(request())

        self.assertEqual(
            response.error_code,
            "SHF-MCP-REGISTRY-TRANSPORT_INVALID",
        )
        self.assertEqual(transport.connect_count, 0)

    def test_client_has_no_resilience_or_secret_ownership(self) -> None:
        source = inspect.getsource(MCPClient).casefold()
        self.assertNotIn("retry", source)
        self.assertNotIn("circuitbreaker", source.replace("_", ""))
        self.assertNotIn("password", source)
        self.assertNotIn("api_key", source)
        self.assertNotIn("authorization", source)
        self.assertNotIn("_server_configs", source)

    @staticmethod
    def _registry(
        server_descriptor: MCPServerDescriptor,
    ) -> MCPServerRegistry:
        registry = MCPServerRegistry()
        registry.register(server_descriptor)
        return registry


if __name__ == "__main__":
    unittest.main()
