import ast
from pathlib import Path


ROOT = Path(__file__).parents[2] / "app" / "composition"


def test_composition_contains_no_task_execution_or_business_calls() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in ROOT.glob("*.py"))
    forbidden = (
        ".execute(",
        ".run(",
        ".create_plan(",
        ".handle(",
        "create_document(",
        "update_document(",
        "convert_document(",
        "export_document(",
    )
    assert all(token not in source for token in forbidden)


def test_composition_has_no_global_component_instances_or_dynamic_imports() -> None:
    for path in ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            assert not isinstance(node, ast.Call) or not (
                isinstance(node.func, ast.Name) and node.func.id == "__import__"
            )
        for node in tree.body:
            if isinstance(node, ast.Assign):
                assert not isinstance(node.value, ast.Call), f"{path.name}包含全局实例"
