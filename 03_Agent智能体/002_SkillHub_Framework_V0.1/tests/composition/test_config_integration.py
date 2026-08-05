import ast
from pathlib import Path

from app.composition import ApplicationFactory, bootstrap
from app.config.models import (
    ApplicationConfig,
    LLMConfig,
    OfficeConfig,
    SecretValue,
    TelegramConfig,
)

from .helpers import dependencies


APP_ROOT = Path(__file__).parents[2] / "app"


def _config(environment="test") -> ApplicationConfig:
    return ApplicationConfig(
        environment=environment,
        llm=LLMConfig("deepseek", SecretValue("deepseek-test-secret")),
        office=OfficeConfig("C:/OfficeCLI/officecli.exe", "1.0.143"),
        telegram=TelegramConfig(False, None),
    )


def test_config_enters_factory_and_container_without_business_propagation() -> None:
    config = _config()
    container = ApplicationFactory().create(dependencies(), config)

    assert container.application_config is config
    assert not hasattr(container.agent, "application_config")
    assert not hasattr(container.gateway, "application_config")
    assert not hasattr(container.telegram_adapter, "application_config")


def test_bootstrap_containers_have_independent_lifecycles() -> None:
    config = _config()
    left = bootstrap(dependencies(), config)
    right = bootstrap(dependencies(), config)

    assert left is not right
    assert left.runtime_manager is not right.runtime_manager
    assert left.skill_registry is not right.skill_registry
    assert left.planner is not right.planner
    assert left.task_plan_executor is not right.task_plan_executor
    assert left.agent is not right.agent
    assert left.gateway is not right.gateway
    assert left.telegram_adapter is not right.telegram_adapter
    assert left.application_config is config
    assert right.application_config is config


def test_bootstrap_contains_no_environment_reads() -> None:
    source = (APP_ROOT / "composition" / "bootstrap.py").read_text(
        encoding="utf-8"
    )
    assert "os.environ" not in source
    assert "os.getenv" not in source
    assert "ConfigLoader" not in source


def test_business_modules_do_not_import_application_config() -> None:
    forbidden_roots = {
        "adapters",
        "core",
        "execution",
        "gateway",
        "planner",
        "runtime",
        "services",
        "skills",
    }
    for path in APP_ROOT.rglob("*.py"):
        relative = path.relative_to(APP_ROOT)
        if relative.parts[0] not in forbidden_roots:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_names = set()
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
        assert "ApplicationConfig" not in imported_names
        assert "app.config.models" not in imported_modules
