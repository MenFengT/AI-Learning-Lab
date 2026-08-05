import unittest

from app.services import (
    AuditServiceProtocol,
    ErrorDescriptor,
    ErrorSeverity,
    MCPClientProtocol,
    RuntimeContextProtocol,
    ServiceConfigProtocol,
    ServiceLayerError,
    validate_error_code,
)


class CompatibleClient:
    def call(self, request: object) -> object:
        return object()


class CompatibleAudit:
    def record(self, event: object) -> None:
        return None


class CompatibleRuntime:
    task_id = "task"
    trace_id = "trace"
    span_id = "span"
    skill_id = "local/demo@0.1.0"


class CompatibleConfig:
    default_timeout_seconds = 1.0
    max_timeout_seconds = 10.0


class ServiceProtocolsTests(unittest.TestCase):
    def test_protocols_support_structural_mock_dependencies(self) -> None:
        self.assertIsInstance(CompatibleClient(), MCPClientProtocol)
        self.assertIsInstance(CompatibleAudit(), AuditServiceProtocol)
        self.assertIsInstance(CompatibleRuntime(), RuntimeContextProtocol)
        self.assertIsInstance(CompatibleConfig(), ServiceConfigProtocol)

    def test_error_model_and_code_validation(self) -> None:
        descriptor = ErrorDescriptor(
            code="SHF-MCP-CLIENT-TIMEOUT",
            severity=ErrorSeverity.ERROR,
            message="MCP调用超时",
            details={"attempts": 2},
        )
        error = ServiceLayerError(descriptor, cause=TimeoutError())

        self.assertEqual(error.descriptor.code, "SHF-MCP-CLIENT-TIMEOUT")
        self.assertEqual(error.descriptor.severity, ErrorSeverity.ERROR)
        self.assertIsInstance(error.cause, TimeoutError)

    def test_invalid_error_code_is_rejected(self) -> None:
        for code in ("MCP-TIMEOUT", "SHF-mcp-CLIENT-TIMEOUT", "SHF-MCP"):
            with self.subTest(code=code), self.assertRaises(ValueError):
                validate_error_code(code)


if __name__ == "__main__":
    unittest.main()
