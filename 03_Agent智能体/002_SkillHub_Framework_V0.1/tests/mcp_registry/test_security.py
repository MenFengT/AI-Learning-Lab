import io
import math
import unittest

from app.mcp_registry import (
    DescriptorValidationError,
    MCPServerDescriptor,
    SecretDetectedError,
    ServerCapabilities,
    ToolDescriptor,
    ToolIdempotency,
    TransportType,
)

from .helpers import descriptor


class FakeTransport:
    def connect(self) -> None:
        return None


class FakeConnection:
    pass


class MCPRegistrySecurityTests(unittest.TestCase):
    def test_secret_keys_are_rejected_recursively(self) -> None:
        secret_cases = (
            {"token": "value"},
            {"nested": {"password": "value"}},
            {"nested": {"api_key": "value"}},
            {"authorization": "value"},
            {"secret": "value"},
            {"access_token": "value"},
        )
        for metadata in secret_cases:
            with self.subTest(metadata=tuple(metadata)), self.assertRaises(
                SecretDetectedError
            ):
                descriptor(metadata=metadata)

    def test_transport_reference_cannot_contain_secret_or_endpoint(self) -> None:
        for reference in (
            "token-value",
            "https://server.example",
            "mcp.server.api_key",
        ):
            with self.subTest(reference=reference), self.assertRaises(
                (DescriptorValidationError, SecretDetectedError)
            ):
                MCPServerDescriptor(
                    server_id="knowledge-server@0.2.0",
                    server_name="knowledge-server",
                    version="0.2.0",
                    description="Server",
                    transport_type=TransportType.HTTP,
                    transport_config_reference=reference,
                    capabilities=ServerCapabilities(tools=False),
                    allowed_tools=(),
                )

    def test_instances_callables_modules_and_file_handles_are_rejected(self) -> None:
        unsafe_values = (
            FakeTransport(),
            FakeConnection(),
            lambda: None,
            math,
            io.StringIO("data"),
        )
        for value in unsafe_values:
            with self.subTest(value=type(value).__name__), self.assertRaises(
                DescriptorValidationError
            ):
                descriptor(metadata={"unsafe": value})

    def test_schema_rejects_callable_and_secret(self) -> None:
        for schema in (
            {"handler": lambda: None},
            {"properties": {"password": {"type": "string"}}},
        ):
            with self.subTest(schema=tuple(schema)), self.assertRaises(
                DescriptorValidationError
            ):
                ToolDescriptor(
                    tool_name="knowledge.query",
                    description="查询知识",
                    input_schema=schema,
                    output_schema={"type": "object"},
                    permission_required="KNOWLEDGE_READ",
                    idempotency=ToolIdempotency.IDEMPOTENT,
                )


if __name__ == "__main__":
    unittest.main()
