import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLANNER_ROOT = PROJECT_ROOT / "app" / "planner"
FORBIDDEN_IMPORT_PREFIXES = (
    "app.skills",
    "app.services",
    "app.mcp_servers",
    "app.mcp_registry",
    "app.knowledge",
    "app.registry",
    "app.tools",
)


class PlannerArchitectureBoundaryTests(unittest.TestCase):
    def test_planner_has_no_forbidden_layer_imports(self) -> None:
        violations: list[str] = []
        for path in sorted(PLANNER_ROOT.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                modules: tuple[str, ...] = ()
                if isinstance(node, ast.Import):
                    modules = tuple(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules = (node.module,)
                for module in modules:
                    if module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                        violations.append(f"{path.name}:{module}")
        self.assertEqual(violations, [])

    def test_planner_contains_no_autonomous_loop(self) -> None:
        while_nodes: list[str] = []
        for path in sorted(PLANNER_ROOT.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            if any(isinstance(node, ast.While) for node in ast.walk(tree)):
                while_nodes.append(path.name)
        self.assertEqual(while_nodes, [])

    def test_planner_exposes_no_execution_or_tool_method(self) -> None:
        forbidden_methods = {"execute", "call_tool", "call_mcp", "run_skill"}
        definitions: set[str] = set()
        for path in sorted(PLANNER_ROOT.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            definitions.update(
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
        self.assertTrue(forbidden_methods.isdisjoint(definitions))


if __name__ == "__main__":
    unittest.main()
