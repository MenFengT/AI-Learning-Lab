import ast
import unittest
from pathlib import Path

import app.content


class ContentArchitectureBoundaryTests(unittest.TestCase):
    def test_content_layer_has_no_forbidden_imports(self) -> None:
        package = Path(app.content.__file__).parent
        forbidden = (
            "app.skills",
            "app.services",
            "app.mcp_servers",
            "app.mcp_registry",
            "app.tools",
            "app.artifact",
            "officecli",
        )
        for source in package.glob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            self.assertFalse(
                any(name.casefold().startswith(forbidden) for name in imports),
                f"{source.name}跨越Content边界：{imports}",
            )

    def test_content_layer_has_no_file_skill_or_mcp_execution(self) -> None:
        package = Path(app.content.__file__).parent
        forbidden_calls = {
            "open",
            "execute",
            "call_mcp",
            "call_tool",
            "read_file",
            "write_file",
            "select_by_id",
            "resolve",
        }
        for source in package.glob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            calls = {
                node.func.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
            }
            names = {
                node.func.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            self.assertTrue(forbidden_calls.isdisjoint(calls | names))


if __name__ == "__main__":
    unittest.main()
