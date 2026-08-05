import unittest

from app.mcp_registry import (
    DescriptorValidationError,
    MCPServerDescriptor,
    ServerCapabilities,
    ToolDescriptor,
    ToolIdempotency,
    TransportType,
    build_server_id,
)

from .helpers import descriptor, tool


class MCPRegistryModelTests(unittest.TestCase):
    def test_descriptor_is_deeply_immutable(self) -> None:
        metadata = {"owner": {"teams": ["platform"]}}
        input_schema = {"type": "object", "required": ["query"]}
        descriptor_tool = ToolDescriptor(
            tool_name="knowledge.query",
            description="查询知识",
            input_schema=input_schema,
            output_schema={"type": "object"},
            permission_required="KNOWLEDGE_READ",
            idempotency=ToolIdempotency.IDEMPOTENT,
        )
        server = descriptor(tools=(descriptor_tool,), metadata=metadata)
        metadata["owner"]["teams"].append("changed")
        input_schema["required"].append("changed")

        self.assertEqual(server.metadata["owner"]["teams"], ("platform",))
        self.assertEqual(
            server.allowed_tools[0].input_schema["required"], ("query",)
        )
        with self.assertRaises(TypeError):
            server.metadata["owner"] = "changed"

    def test_stable_server_id_is_required(self) -> None:
        with self.assertRaisesRegex(
            DescriptorValidationError, "server_id必须为"
        ):
            MCPServerDescriptor(
                server_id="random-id",
                server_name="knowledge-server",
                version="0.2.0",
                description="Server",
                transport_type=TransportType.IN_MEMORY,
                transport_config_reference="mcp.knowledge.local",
                capabilities=ServerCapabilities(tools=True),
                allowed_tools=(tool(),),
            )
        self.assertEqual(
            build_server_id("knowledge-server", "0.2.0"),
            "knowledge-server@0.2.0",
        )

    def test_duplicate_tools_and_invalid_capabilities_are_rejected(self) -> None:
        duplicate = tool()
        with self.assertRaisesRegex(DescriptorValidationError, "不能重复"):
            descriptor(tools=(duplicate, duplicate))
        with self.assertRaisesRegex(DescriptorValidationError, "allowed_tools"):
            MCPServerDescriptor(
                server_id="knowledge-server@0.2.0",
                server_name="knowledge-server",
                version="0.2.0",
                description="Server",
                transport_type=TransportType.IN_MEMORY,
                transport_config_reference="mcp.knowledge.local",
                capabilities=ServerCapabilities(tools=False),
                allowed_tools=(tool(),),
            )

    def test_tool_schema_rejects_code_strings(self) -> None:
        with self.assertRaisesRegex(DescriptorValidationError, "代码字符串"):
            ToolDescriptor(
                tool_name="knowledge.query",
                description="查询知识",
                input_schema={"default": "__import__('os')"},
                output_schema={"type": "object"},
                permission_required="KNOWLEDGE_READ",
                idempotency=ToolIdempotency.IDEMPOTENT,
            )


if __name__ == "__main__":
    unittest.main()
