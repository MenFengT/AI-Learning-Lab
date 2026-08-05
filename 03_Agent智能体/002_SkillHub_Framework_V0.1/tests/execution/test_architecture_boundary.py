import ast
import unittest
from pathlib import Path

import app.execution


class ExecutionArchitectureBoundaryTests(unittest.TestCase):
    def test_executor_does_not_import_forbidden_layers(self) -> None:
        package = Path(app.execution.__file__).parent
        forbidden = (
            "app.services",
            "app.mcp_servers",
            "app.mcp_registry",
            "app.knowledge",
            "app.tools",
            "app.skills",
        )
        for source_path in package.glob("*.py"):
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            self.assertFalse(
                any(name.startswith(forbidden) for name in imports),
                f"{source_path.name}跨越执行边界：{imports}",
            )

    def test_executor_has_no_llm_or_infrastructure_control_loop(self) -> None:
        source = Path(app.execution.__file__).parent / "executor.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(node, ast.While) for node in ast.walk(tree)))
        forbidden_calls = {"call_tool", "call_mcp", "query_knowledge"}
        called = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue(forbidden_calls.isdisjoint(called))

    def test_executor_does_not_store_resolved_skill(self) -> None:
        source = Path(app.execution.__file__).parent / "executor.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        assigned_attributes = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.ctx, ast.Store)
        }
        self.assertNotIn("_skill", assigned_attributes)
        self.assertNotIn("_skills", assigned_attributes)


if __name__ == "__main__":
    unittest.main()
