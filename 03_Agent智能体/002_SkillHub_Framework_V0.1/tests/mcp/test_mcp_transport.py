import unittest

from app.services.mcp import (
    ConnectionManager,
    FakeTransport,
    MCPServerConfigurationError,
    MCPTransportConnectionError,
    ServerConfig,
)


def config() -> ServerConfig:
    return ServerConfig(
        server_name="filesystem-server",
        transport_name="fake",
        allowed_tools=frozenset({"read-file"}),
        connect_timeout=1.0,
        max_request_timeout=5.0,
    )


class MCPTransportTests(unittest.TestCase):
    def test_fake_transport_requires_connection_and_copies_payload(self) -> None:
        transport = FakeTransport({"content": "ok"})
        with self.assertRaises(MCPTransportConnectionError):
            transport.send({"value": [1]}, 1.0)

        payload = {"value": [1]}
        transport.connect(config())
        response = transport.send(payload, 1.0)
        payload["value"].append(2)

        self.assertEqual(transport.last_payload, {"value": [1]})
        self.assertEqual(response, {"content": "ok"})

    def test_connection_manager_releases_successful_connection(self) -> None:
        transport = FakeTransport({"content": "ok"})
        manager = ConnectionManager({"fake": lambda: transport})

        with manager.connection(config()) as connected:
            self.assertIs(connected, transport)
            self.assertTrue(transport.is_connected())

        self.assertFalse(transport.is_connected())
        self.assertEqual(transport.close_count, 1)

    def test_connection_manager_releases_connection_on_error(self) -> None:
        transport = FakeTransport({"content": "ok"})
        manager = ConnectionManager({"fake": lambda: transport})

        with self.assertRaisesRegex(RuntimeError, "call failed"):
            with manager.connection(config()):
                raise RuntimeError("call failed")

        self.assertFalse(transport.is_connected())
        self.assertEqual(transport.close_count, 1)

    def test_unknown_transport_is_rejected(self) -> None:
        manager = ConnectionManager({})
        with self.assertRaises(MCPServerConfigurationError):
            with manager.connection(config()):
                pass


if __name__ == "__main__":
    unittest.main()
