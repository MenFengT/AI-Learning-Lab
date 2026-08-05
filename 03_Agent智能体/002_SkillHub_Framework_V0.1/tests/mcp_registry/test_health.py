import unittest

from app.mcp_registry import (
    ServerHealthStatus,
    check_server_health,
)

from .helpers import descriptor


class RecordingAvailability:
    def __init__(self, supported: bool) -> None:
        self.supported = supported
        self.calls: list[tuple[str, str]] = []

    def supports(
        self, transport_type: str, transport_config_reference: str
    ) -> bool:
        self.calls.append((transport_type, transport_config_reference))
        return self.supported


class FailingAvailability:
    def supports(
        self, transport_type: str, transport_config_reference: str
    ) -> bool:
        raise RuntimeError("provider unavailable")


class MCPServerHealthTests(unittest.TestCase):
    def test_complete_descriptor_and_transport_are_healthy(self) -> None:
        availability = RecordingAvailability(True)
        server = descriptor(health=ServerHealthStatus.UNKNOWN)

        result = check_server_health(server, availability)

        self.assertEqual(result.status, ServerHealthStatus.HEALTHY)
        self.assertEqual(result.errors, ())
        self.assertIn("transport_available", result.checks)
        self.assertEqual(len(availability.calls), 1)
        self.assertEqual(server.health_status, ServerHealthStatus.UNKNOWN)

    def test_unavailable_transport_is_unhealthy(self) -> None:
        result = check_server_health(
            descriptor(health=ServerHealthStatus.UNKNOWN),
            RecordingAvailability(False),
        )

        self.assertEqual(result.status, ServerHealthStatus.UNHEALTHY)
        self.assertIn("Transport类型或配置引用不可用", result.errors)

    def test_health_check_has_no_tool_execution_dependency(self) -> None:
        availability = RecordingAvailability(True)

        result = check_server_health(descriptor(), availability)

        self.assertEqual(result.status, ServerHealthStatus.HEALTHY)
        self.assertFalse(hasattr(availability, "call_tool"))
        self.assertFalse(hasattr(availability, "connect"))

    def test_transport_probe_failure_becomes_unhealthy_result(self) -> None:
        result = check_server_health(descriptor(), FailingAvailability())

        self.assertEqual(result.status, ServerHealthStatus.UNHEALTHY)
        self.assertIn(
            "Transport可用性检查失败：RuntimeError", result.errors
        )


if __name__ == "__main__":
    unittest.main()
