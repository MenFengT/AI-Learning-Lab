import unittest

from app.mcp_registry import (
    ActiveServerConflictError,
    DuplicateServerError,
    MCPServerCatalogProtocol,
    MCPServerRegistry,
    ServerCapability,
    ServerDisabledError,
)

from .helpers import descriptor


class MCPServerRegistryTests(unittest.TestCase):
    def test_register_query_list_and_unregister(self) -> None:
        registry = MCPServerRegistry()
        server = descriptor()

        registry.register(server)

        self.assertIsInstance(registry, MCPServerCatalogProtocol)
        self.assertIs(registry.get("knowledge-server"), server)
        self.assertIs(
            registry.get_version("knowledge-server", "0.2.0"), server
        )
        self.assertEqual(registry.list_all(), (server,))
        self.assertEqual(
            registry.find_by_capability(ServerCapability.TOOLS), (server,)
        )
        self.assertIs(registry.unregister(server.server_id), server)
        self.assertEqual(registry.list_all(), ())

    def test_duplicate_server_id_is_rejected(self) -> None:
        registry = MCPServerRegistry()
        server = descriptor()
        registry.register(server)

        with self.assertRaises(DuplicateServerError):
            registry.register(server)

    def test_only_one_enabled_version_per_name(self) -> None:
        registry = MCPServerRegistry()
        registry.register(descriptor(version="0.1.0"))

        with self.assertRaises(ActiveServerConflictError):
            registry.register(descriptor(version="0.2.0"))

    def test_disabled_versions_can_be_retained(self) -> None:
        registry = MCPServerRegistry()
        old = descriptor(version="0.1.0", enabled=False)
        current = descriptor(version="0.2.0")
        registry.register(old)
        registry.register(current)

        self.assertIs(registry.get("knowledge-server"), current)
        self.assertIs(
            registry.get_version("knowledge-server", "0.1.0"), old
        )
        self.assertEqual(len(registry.list_all()), 2)

    def test_only_disabled_server_is_not_default_target(self) -> None:
        registry = MCPServerRegistry()
        registry.register(descriptor(enabled=False))

        with self.assertRaises(ServerDisabledError):
            registry.get("knowledge-server")


if __name__ == "__main__":
    unittest.main()
