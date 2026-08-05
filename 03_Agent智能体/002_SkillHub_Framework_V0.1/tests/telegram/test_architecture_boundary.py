import ast
import unittest
from pathlib import Path

import app.adapters.telegram


class TelegramArchitectureBoundaryTests(unittest.TestCase):
    def test_adapter_only_depends_on_gateway_contracts(self) -> None:
        package = Path(app.adapters.telegram.__file__).parent
        forbidden_imports = (
            "app.core",
            "app.planner",
            "app.execution",
            "app.skills",
            "app.services",
            "app.mcp_servers",
            "app.mcp_registry",
            "app.tools",
            "app.knowledge",
            "app.artifact",
            "app.ingestion",
            "telegram",
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

    def test_adapter_has_no_sdk_token_file_or_internal_calls(self) -> None:
        package = Path(app.adapters.telegram.__file__).parent
        forbidden_calls = {
            "open",
            "download_file",
            "get_file",
            "execute",
            "select_by_id",
            "call_mcp",
            "call_tool",
            "read_file",
            "write_file",
        }
        for source in package.glob("*.py"):
            text = source.read_text(encoding="utf-8")
            self.assertNotIn("BOT_TOKEN", text)
            tree = ast.parse(text)
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


if __name__ == "__main__":
    unittest.main()
