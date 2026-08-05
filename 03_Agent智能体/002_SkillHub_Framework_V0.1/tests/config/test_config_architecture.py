import ast
from pathlib import Path


APP_ROOT = Path(__file__).parents[2] / "app"


def test_skill_service_and_adapter_do_not_read_environment_directly() -> None:
    for folder in ("skills", "services", "adapters"):
        for path in (APP_ROOT / folder).rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert "os.environ" not in source
            assert "os.getenv" not in source
            assert "environ.get" not in source


def test_application_config_is_not_imported_by_business_layers() -> None:
    forbidden_roots = {"skills", "services", "adapters", "runtime", "planner", "execution"}
    for path in APP_ROOT.rglob("*.py"):
        relative = path.relative_to(APP_ROOT)
        if relative.parts[0] not in forbidden_roots:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
        assert "app.config.models" not in imports
        assert "app.config.config" not in imports
