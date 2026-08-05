from dataclasses import FrozenInstanceError

import pytest

from app.config.loader import ConfigLoader
from app.config.models import SecretValue
from app.config.errors import MissingConfigurationError


def _environment(**overrides):
    values = {
        "APP_ENV": "test",
        "DEEPSEEK_API_KEY": "deepseek-secret-value",
        "OFFICECLI_PATH": "C:/OfficeCLI/officecli.exe",
        "OFFICECLI_VERSION": "1.0.143",
        "TELEGRAM_ENABLED": "true",
        "TELEGRAM_BOT_TOKEN": "telegram-secret-value",
    }
    values.update(overrides)
    return values


def test_loads_environment_into_application_config() -> None:
    config = ConfigLoader().load(environ=_environment())

    assert config.environment == "test"
    assert config.llm.provider == "deepseek"
    assert config.llm.api_key.get_secret_value() == "deepseek-secret-value"
    assert config.office.executable_path == "C:/OfficeCLI/officecli.exe"
    assert config.office.version == "1.0.143"
    assert config.telegram.enabled is True


def test_dotenv_is_loaded_and_explicit_environment_overrides(tmp_path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "APP_ENV=development\n"
        "DEEPSEEK_API_KEY=from-file\n"
        "OFFICECLI_PATH='C:/OfficeCLI/officecli.exe'\n"
        "TELEGRAM_ENABLED=false\n",
        encoding="utf-8",
    )

    config = ConfigLoader().load(
        dotenv,
        environ={"APP_ENV": "production"},
    )

    assert config.environment == "production"
    assert config.llm.api_key.get_secret_value() == "from-file"
    assert config.telegram.enabled is False
    assert config.telegram.bot_token is None


@pytest.mark.parametrize(
    "missing",
    ("APP_ENV", "DEEPSEEK_API_KEY", "OFFICECLI_PATH"),
)
def test_missing_required_configuration_raises(missing) -> None:
    values = _environment()
    values.pop(missing)
    with pytest.raises(MissingConfigurationError) as error:
        ConfigLoader().load(environ=values)
    assert "secret-value" not in str(error.value)


def test_secrets_are_masked_in_string_repr_and_safe_snapshot() -> None:
    config = ConfigLoader().load(environ=_environment())
    text = f"{config!r} {config.llm.api_key!s} {config.to_safe_dict()!r}"

    assert "deepseek-secret-value" not in text
    assert "telegram-secret-value" not in text
    assert "********alue" in text
    assert isinstance(config.llm.api_key, SecretValue)


def test_configuration_is_immutable() -> None:
    config = ConfigLoader().load(environ=_environment())
    with pytest.raises(FrozenInstanceError):
        config.environment = "production"
    with pytest.raises(FrozenInstanceError):
        config.llm.provider = "other"
    with pytest.raises(TypeError):
        config.to_safe_dict()["environment"] = "other"
