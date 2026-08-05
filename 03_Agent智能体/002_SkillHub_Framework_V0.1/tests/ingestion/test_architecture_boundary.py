import ast
import unittest
from pathlib import Path

import app.ingestion


class IngestionArchitectureBoundaryTests(unittest.TestCase):
    def test_ingestion_only_depends_on_gateway_runtime_and_filesystem_contracts(self) -> None:
        package = Path(app.ingestion.__file__).parent
        forbidden_imports = (
            "app.skills",
            "app.services.office",
            "app.services.knowledge",
            "app.services.mcp",
            "app.mcp_servers",
            "app.mcp_registry",
            "app.tools",
            "app.artifact",
            "app.planner",
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
                any(name.startswith(forbidden_imports) for name in imports),
                f"{source.name}: {imports}",
            )

    def test_ingestion_cannot_read_modify_or_execute_files(self) -> None:
        source = Path(app.ingestion.__file__).parent / "service.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        forbidden = {
            "open",
            "read_file",
            "write_file",
            "copy_file",
            "move_file",
            "rename_file",
            "archive_file",
            "request_delete",
            "confirm_delete",
            "call_mcp",
            "call_tool",
            "execute",
        }
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
        self.assertTrue(forbidden.isdisjoint(calls | names))
        self.assertIn("list_files", calls)


if __name__ == "__main__":
    unittest.main()
