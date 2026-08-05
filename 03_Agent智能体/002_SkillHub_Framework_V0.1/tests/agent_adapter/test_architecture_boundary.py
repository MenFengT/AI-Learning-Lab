import ast
from pathlib import Path


ADAPTER_ROOT = Path(__file__).parents[2] / "app" / "adapters" / "agent"
FORBIDDEN_IMPORT_PREFIXES = (
    "app.core",
    "app.planner",
    "app.execution",
    "app.skills",
    "app.services",
    "app.runtime",
    "app.mcp_registry",
    "app.mcp_servers",
    "app.knowledge",
    "app.tools",
)


def test_adapter_has_only_protocol_conversion_dependencies() -> None:
    for source_path in ADAPTER_ROOT.glob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        assert not any(
            name.startswith(prefix)
            for name in imported
            for prefix in FORBIDDEN_IMPORT_PREFIXES
        ), f"{source_path.name} 越界导入: {imported}"


def test_adapter_contains_no_planning_or_infrastructure_calls() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8").casefold()
        for path in ADAPTER_ROOT.glob("*.py")
    )
    forbidden = (
        "skill_router",
        "planner",
        "mcpclient",
        "filesystemservice",
        "officeservice",
        "open(",
        "subprocess",
    )
    assert all(token not in source for token in forbidden)
