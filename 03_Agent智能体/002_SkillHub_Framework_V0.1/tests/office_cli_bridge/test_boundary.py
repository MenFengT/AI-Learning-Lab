import ast
from pathlib import Path


ROOT = Path(__file__).parents[2] / "app" / "mcp_servers" / "office" / "runtime" / "mcp_bridge"


def test_bridge_does_not_use_process_shell_or_network_implementation() -> None:
    imports = []
    source = ""
    for path in ROOT.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        source += text.casefold()
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
    forbidden_imports = ("subprocess", "os", "socket", "requests", "httpx", "pathlib")
    assert not any(name.startswith(forbidden_imports) for name in imports)
    assert "popen(" not in source
    assert "system(" not in source
    assert "shell=true" not in source


def test_bridge_does_not_depend_on_business_layers() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in ROOT.glob("*.py"))
    forbidden = ("app.skills", "app.gateway", "app.planner", "app.core", "app.content")
    assert all(name not in source for name in forbidden)
