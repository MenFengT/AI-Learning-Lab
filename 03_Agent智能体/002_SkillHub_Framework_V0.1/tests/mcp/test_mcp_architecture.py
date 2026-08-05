import ast
import unittest
from pathlib import Path

from app.services.mcp import (
    FakeTransport,
    MCPClient,
    MCPClientProtocol,
    MCPTransportProtocol,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MCP_ROOT = PROJECT_ROOT / "app" / "services" / "mcp"


class MCPArchitectureTests(unittest.TestCase):
    def test_client_and_transport_match_protocols(self) -> None:
        self.assertIsInstance(FakeTransport(), MCPTransportProtocol)
        self.assertTrue(hasattr(MCPClient, "call"))
        self.assertIn("call", MCPClientProtocol.__dict__)

    def test_mcp_infrastructure_has_no_forbidden_dependencies(self) -> None:
        forbidden_prefixes = (
            "app.core.agent",
            "app.core.skill_router",
            "app.registry",
            "app.runtime",
            "app.skills",
            "subprocess",
        )
        for path in MCP_ROOT.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            violations = [
                name
                for name in imports
                if name.startswith(forbidden_prefixes)
                or "retry" in name.casefold()
                or "circuit" in name.casefold()
            ]
            self.assertEqual(violations, [], f"{path.name}: {violations}")

    def test_client_call_contains_no_retry_loop_or_shell_call(self) -> None:
        path = MCP_ROOT / "client.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        client_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "MCPClient"
        )
        call_method = next(
            node
            for node in client_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "call"
        )
        loops = [
            node
            for node in ast.walk(call_method)
            if isinstance(node, (ast.For, ast.While, ast.AsyncFor))
        ]
        self.assertEqual(loops, [])
        source = path.read_text(encoding="utf-8").casefold()
        self.assertNotIn("subprocess", source)
        self.assertNotIn("os.system", source)
        self.assertNotIn("officecli", source)


if __name__ == "__main__":
    unittest.main()
