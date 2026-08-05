import ast
import unittest
from pathlib import Path

from app.skills.document import skill


class DocumentBoundaryTests(unittest.TestCase):
    def test_document_skill_has_no_forbidden_imports(self) -> None:
        source = Path(skill.__file__)
        tree = ast.parse(source.read_text(encoding="utf-8"))
        forbidden = (
            "app.services.mcp",
            "app.mcp_servers",
            "app.mcp_registry",
            "app.services.filesystem",
            "app.tools",
            "officecli",
        )
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        self.assertFalse(
            any(name.casefold().startswith(forbidden) for name in imports),
            imports,
        )

    def test_document_skill_does_not_call_infrastructure_or_other_skills(self) -> None:
        source = Path(skill.__file__)
        tree = ast.parse(source.read_text(encoding="utf-8"))
        forbidden_calls = {
            "call_mcp",
            "call_tool",
            "read_file",
            "write_file",
            "resolve",
            "select",
            "select_by_id",
        }
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue(forbidden_calls.isdisjoint(calls))


if __name__ == "__main__":
    unittest.main()
