import ast
import unittest
from pathlib import Path

import app.artifact


class ArtifactArchitectureBoundaryTests(unittest.TestCase):
    def test_artifact_does_not_import_forbidden_layers(self) -> None:
        package = Path(app.artifact.__file__).parent
        forbidden = (
            "app.services.mcp",
            "app.mcp_servers",
            "app.mcp_registry",
            "app.tools",
            "app.skills",
            "officecli",
        )
        for source_path in package.glob("*.py"):
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            self.assertFalse(
                any(name.casefold().startswith(forbidden) for name in imports),
                f"{source_path.name}跨越Artifact边界：{imports}",
            )

    def test_service_does_not_perform_file_or_tool_operations(self) -> None:
        source = Path(app.artifact.__file__).parent / "service.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        forbidden_calls = {
            "open",
            "read_file",
            "write_file",
            "call_mcp",
            "call_tool",
            "execute",
        }
        names = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        attributes = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue(forbidden_calls.isdisjoint(names | attributes))


if __name__ == "__main__":
    unittest.main()
