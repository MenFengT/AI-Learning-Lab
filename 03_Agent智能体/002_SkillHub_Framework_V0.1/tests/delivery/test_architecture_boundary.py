import ast
from pathlib import Path


DELIVERY_ROOT = Path(__file__).parents[2] / "app" / "delivery"
FORBIDDEN = (
    "app.services.filesystem",
    "app.services.office",
    "app.skills",
    "app.core",
    "app.gateway",
    "app.mcp_servers",
    "app.services.mcp",
)


def test_delivery_has_no_forbidden_layer_dependencies() -> None:
    for path in DELIVERY_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        assert not any(
            name.startswith(prefix) for name in imports for prefix in FORBIDDEN
        ), f"{path.name}越界依赖：{imports}"


def test_delivery_does_not_read_files_or_call_business_components() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8").casefold()
        for path in DELIVERY_ROOT.glob("*.py")
    )
    forbidden_tokens = (
        "open(", "read_bytes", "read_text", "filesystemservice",
        "officeservice", "skill.execute", "agent.run", "mcpclient",
    )
    assert all(token not in source for token in forbidden_tokens)
