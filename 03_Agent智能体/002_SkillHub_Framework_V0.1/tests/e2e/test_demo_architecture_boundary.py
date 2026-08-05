import ast
from pathlib import Path


DEMO_REQUEST = Path(__file__).parents[2] / "app" / "demo" / "demo_request.py"


def test_demo_entry_only_enters_through_telegram_adapter() -> None:
    source = DEMO_REQUEST.read_text(encoding="utf-8")
    assert ".telegram_adapter.handle(" in source
    forbidden = (
        "DocumentSkill(",
        ".create_plan(",
        ".execute(",
        "ArtifactService(",
        "OfficeService(",
    )
    assert all(token not in source for token in forbidden)


def test_demo_does_not_use_shell_or_network_sdk() -> None:
    root = DEMO_REQUEST.parent
    imports = []
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
    assert not any(name.startswith(("subprocess", "telegram", "requests", "httpx")) for name in imports)
