import ast
import unittest
from pathlib import Path

import app.services.content


class ContentServiceArchitectureBoundaryTests(unittest.TestCase):
    def test_service_has_no_forbidden_dependencies_or_calls(self) -> None:
        package = Path(app.services.content.__file__).parent
        forbidden_imports = (
            "app.skills",
            "app.services.mcp",
            "app.mcp_servers",
            "app.mcp_registry",
            "app.services.filesystem",
            "app.services.office",
            "app.tools",
            "app.artifact",
        )
        forbidden_calls = {
            "open",
            "call_mcp",
            "call_tool",
            "read_file",
            "write_file",
            "create_document",
            "execute",
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
            self.assertTrue(forbidden_calls.isdisjoint(calls))


if __name__ == "__main__":
    unittest.main()
