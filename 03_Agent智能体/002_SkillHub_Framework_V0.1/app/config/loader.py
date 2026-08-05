"""从.env和进程环境构建不可变ApplicationConfig。"""

from collections.abc import Mapping
import os
from pathlib import Path

from .errors import (
    ConfigurationFileError,
    InvalidConfigurationError,
    MissingConfigurationError,
)
from .models import (
    ApplicationConfig,
    LLMConfig,
    OfficeConfig,
    SecretValue,
    TelegramConfig,
)


_SUPPORTED_KEYS = frozenset(
    {
        "APP_ENV",
        "DEEPSEEK_API_KEY",
        "LLM_PROVIDER",
        "OFFICECLI_PATH",
        "OFFICECLI_VERSION",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_ENABLED",
    }
)


class ConfigLoader:
    """唯一允许读取进程环境变量的配置入口。"""

    def load(
        self,
        dotenv_path: Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> ApplicationConfig:
        values: dict[str, str] = {}
        if dotenv_path is not None:
            values.update(self._read_dotenv(dotenv_path))
        source = os.environ if environ is None else environ
        values.update(
            {
                key: str(value)
                for key, value in source.items()
                if key in _SUPPORTED_KEYS
            }
        )
        return self._build(values)

    @staticmethod
    def _read_dotenv(path: Path) -> dict[str, str]:
        if not isinstance(path, Path):
            raise InvalidConfigurationError("dotenv_path必须是Path")
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigurationFileError(".env读取失败") from exc
        values: dict[str, str] = {}
        for line_number, raw_line in enumerate(content.splitlines(), 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            if "=" not in line:
                raise InvalidConfigurationError(
                    f".env第{line_number}行格式无效"
                )
            key, raw_value = line.split("=", 1)
            key = key.strip()
            if key not in _SUPPORTED_KEYS:
                continue
            value = raw_value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            values[key] = value
        return values

    @staticmethod
    def _build(values: Mapping[str, str]) -> ApplicationConfig:
        environment = _required(values, "APP_ENV")
        llm_provider = values.get("LLM_PROVIDER", "deepseek").strip()
        api_key = SecretValue(_required(values, "DEEPSEEK_API_KEY"))
        executable_path = _required(values, "OFFICECLI_PATH")
        office_version = values.get("OFFICECLI_VERSION", "unverified").strip()
        if not office_version:
            office_version = "unverified"
        token_text = values.get("TELEGRAM_BOT_TOKEN", "").strip()
        token = SecretValue(token_text) if token_text else None
        enabled = _boolean(
            values.get("TELEGRAM_ENABLED"),
            default=token is not None,
        )
        return ApplicationConfig(
            environment=environment,
            llm=LLMConfig(llm_provider, api_key),
            office=OfficeConfig(executable_path, office_version),
            telegram=TelegramConfig(enabled, token),
        )


def _required(values: Mapping[str, str], key: str) -> str:
    value = values.get(key, "").strip()
    if not value:
        raise MissingConfigurationError(f"缺少必需配置：{key}")
    return value


def _boolean(value: str | None, *, default: bool) -> bool:
    if value is None or not value.strip():
        return default
    normalized = value.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise InvalidConfigurationError("布尔配置值无效")
