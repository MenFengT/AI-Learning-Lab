import ast
from pathlib import Path


RUNTIME_ROOT = Path(__file__).parents[2] / "app" / "mcp_servers" / "office" / "runtime"


def test_adapter_does_not_use_shell_or_user_commands() -> None:
    sources = [path.read_text(encoding="utf-8") for path in RUNTIME_ROOT.glob("*.py")]
    imports = []
    for source in sources:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
    assert not any(name.startswith(("subprocess", "os", "pathlib")) for name in imports)
    combined = "\n".join(sources).casefold()
    assert "shell=true" not in combined
    assert "popen(" not in combined
    assert "system(" not in combined


def test_adapter_does_not_depend_on_upper_business_layers() -> None:
    forbidden = ("app.skills", "app.gateway", "app.planner", "app.core", "app.runtime")
    for path in RUNTIME_ROOT.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert all(name not in source for name in forbidden)
