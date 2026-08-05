import ast
import unittest
from pathlib import Path

import app.gateway


class GatewayArchitectureBoundaryTests(unittest.TestCase):
    def test_gateway_has_no_forbidden_imports_or_calls(self) -> None:
        package = Path(app.gateway.__file__).parent
        forbidden_imports = (
            "app.skills",
            "app.services",
            "app.mcp_servers",
            "app.mcp_registry",
            "app.tools",
            "app.knowledge",
            "app.artifact",
            "app.planner",
        )
        forbidden_calls = {
            "open",
            "execute",
            "select",
            "select_by_id",
            "call_mcp",
            "call_tool",
            "read_file",
            "write_file",
        }
        for source in package.glob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            self.assertFalse(
                any(name.startswith(forbidden_imports) for name in imports),
                f"{source.name}: {imports}",
            )
            calls = {
                node.func.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            }
            names = {
                node.func.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            self.assertTrue(forbidden_calls.isdisjoint(calls | names))

    def test_gateway_is_not_an_agent_or_autonomous_loop(self) -> None:
        package = Path(app.gateway.__file__).parent
        for source in package.glob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            self.assertFalse(any(isinstance(node, ast.While) for node in ast.walk(tree)))
            bases = {
                base.id
                for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef)
                for base in node.bases
                if isinstance(base, ast.Name)
            }
            self.assertNotIn("BaseSkill", bases)


if __name__ == "__main__":
    unittest.main()
