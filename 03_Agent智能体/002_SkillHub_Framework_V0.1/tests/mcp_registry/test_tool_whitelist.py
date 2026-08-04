import unittest

from app.mcp_registry import (
    MCPServerRegistry,
    ServerHealthStatus,
    ServerUnhealthyError,
    ToolNotAllowedError,
)

from .helpers import descriptor, tool


class ToolWhitelistTests(unittest.TestCase):
    def test_registered_tool_and_permission_are_returned(self) -> None:
        registry = MCPServerRegistry()
        registered_tool = tool(permission="KNOWLEDGE_READ")
        registry.register(descriptor(tools=(registered_tool,)))

        selected = registry.validate_tool(
            "knowledge-server", "knowledge.query"
        )

        self.assertIs(selected, registered_tool)
        self.assertEqual(selected.permission_required, "KNOWLEDGE_READ")

    def test_tool_outside_fixed_whitelist_is_rejected(self) -> None:
        registry = MCPServerRegistry()
        registry.register(descriptor())

        with self.assertRaises(ToolNotAllowedError):
            registry.validate_tool(
                "knowledge-server", "filesystem.read"
            )

    def test_unhealthy_server_tool_is_rejected(self) -> None:
        registry = MCPServerRegistry()
        registry.register(
            descriptor(health=ServerHealthStatus.UNHEALTHY)
        )

        with self.assertRaises(ServerUnhealthyError):
            registry.validate_tool(
                "knowledge-server", "knowledge.query"
            )


if __name__ == "__main__":
    unittest.main()
