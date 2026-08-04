"""Service Layer统一错误等级、错误码和异常模型。"""

from dataclasses import dataclass, field
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, Mapping


_ERROR_CODE_PATTERN = re.compile(
    r"^SHF-[A-Z][A-Z0-9]*-[A-Z][A-Z0-9_]*-[A-Z][A-Z0-9_]*$"
)


class ErrorSeverity(str, Enum):
    FATAL = "FATAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass(frozen=True)
class ErrorDescriptor:
    """可跨Service使用的稳定错误描述，不携带异常堆栈。"""

    code: str
    severity: ErrorSeverity
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_error_code(self.code)
        if not self.message.strip():
            raise ValueError("错误message不能为空")
        object.__setattr__(
            self, "details", MappingProxyType(dict(self.details))
        )


class ServiceLayerError(Exception):
    """Service基础设施异常；公开消息与内部原因保持分离。"""

    def __init__(
        self,
        descriptor: ErrorDescriptor,
        *,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(descriptor.message)
        self.descriptor = descriptor
        self.cause = cause


def validate_error_code(code: str) -> None:
    if not _ERROR_CODE_PATTERN.fullmatch(code):
        raise ValueError(
            "错误码必须符合SHF-{LAYER}-{DOMAIN}-{ERROR}格式："
            f"{code}"
        )
