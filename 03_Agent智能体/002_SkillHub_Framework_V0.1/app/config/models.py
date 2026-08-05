"""应用配置的不可变、可脱敏数据契约。"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .errors import InvalidConfigurationError


@dataclass(frozen=True, repr=False)
class SecretValue:
    """显式访问、默认脱敏的Secret包装。"""

    _value: str

    def __post_init__(self) -> None:
        if not isinstance(self._value, str) or not self._value.strip():
            raise InvalidConfigurationError("Secret不能为空")
        object.__setattr__(self, "_value", self._value.strip())

    def get_secret_value(self) -> str:
        return self._value

    def masked(self) -> str:
        if len(self._value) <= 4:
            return "********"
        return f"********{self._value[-4:]}"

    def __str__(self) -> str:
        return self.masked()

    def __repr__(self) -> str:
        return f"SecretValue('{self.masked()}')"


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    api_key: SecretValue

    def __post_init__(self) -> None:
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise InvalidConfigurationError("LLM provider不能为空")
        if not isinstance(self.api_key, SecretValue):
            raise InvalidConfigurationError("LLM api_key必须是SecretValue")
        object.__setattr__(self, "provider", self.provider.strip().casefold())


@dataclass(frozen=True)
class OfficeConfig:
    executable_path: str
    version: str

    def __post_init__(self) -> None:
        if not isinstance(self.executable_path, str) or not self.executable_path.strip():
            raise InvalidConfigurationError("OfficeCLI executable_path不能为空")
        if not isinstance(self.version, str) or not self.version.strip():
            raise InvalidConfigurationError("OfficeCLI version不能为空")
        object.__setattr__(self, "executable_path", self.executable_path.strip())
        object.__setattr__(self, "version", self.version.strip())


@dataclass(frozen=True)
class TelegramConfig:
    enabled: bool
    bot_token: SecretValue | None

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise InvalidConfigurationError("Telegram enabled必须是bool")
        if self.bot_token is not None and not isinstance(self.bot_token, SecretValue):
            raise InvalidConfigurationError("Telegram bot_token必须是SecretValue")
        if self.enabled and self.bot_token is None:
            raise InvalidConfigurationError("启用Telegram时必须配置bot_token")


@dataclass(frozen=True)
class ApplicationConfig:
    environment: str
    llm: LLMConfig
    office: OfficeConfig
    telegram: TelegramConfig

    def __post_init__(self) -> None:
        if not isinstance(self.environment, str) or not self.environment.strip():
            raise InvalidConfigurationError("Application environment不能为空")
        if not isinstance(self.llm, LLMConfig):
            raise InvalidConfigurationError("llm配置无效")
        if not isinstance(self.office, OfficeConfig):
            raise InvalidConfigurationError("office配置无效")
        if not isinstance(self.telegram, TelegramConfig):
            raise InvalidConfigurationError("telegram配置无效")
        object.__setattr__(self, "environment", self.environment.strip().casefold())

    def to_safe_dict(self) -> Mapping[str, object]:
        """仅返回适合日志和诊断展示的脱敏快照。"""
        return MappingProxyType(
            {
                "environment": self.environment,
                "llm": MappingProxyType(
                    {
                        "provider": self.llm.provider,
                        "api_key": self.llm.api_key.masked(),
                    }
                ),
                "office": MappingProxyType(
                    {
                        "executable_path": self.office.executable_path,
                        "version": self.office.version,
                    }
                ),
                "telegram": MappingProxyType(
                    {
                        "enabled": self.telegram.enabled,
                        "bot_token": (
                            self.telegram.bot_token.masked()
                            if self.telegram.bot_token is not None
                            else None
                        ),
                    }
                ),
            }
        )
