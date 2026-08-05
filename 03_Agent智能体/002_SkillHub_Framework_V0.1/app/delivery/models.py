"""Artifact Delivery Layer 不可变数据契约。"""

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
import re
from types import MappingProxyType, ModuleType
from typing import Any, Mapping

from app.runtime.invocation_context import InvocationContext

from .errors import DeliveryRequestError, DeliveryResultError


_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SENSITIVE_KEYS = frozenset(
    {"api_key", "apikey", "authorization", "password", "secret", "token"}
)


class DeliveryTargetType(str, Enum):
    TELEGRAM = "TELEGRAM"
    WEB = "WEB"
    WECHAT = "WECHAT"
    EMAIL = "EMAIL"


class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class DeliveryTarget:
    """通道无关交付目标；不保存Token或连接对象。"""

    target_type: DeliveryTargetType
    recipient_reference: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.target_type, DeliveryTargetType):
            raise DeliveryRequestError("target_type无效")
        _validate_id(self.recipient_reference, "recipient_reference")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class ArtifactDeliveryReference:
    """交付层允许接收的最小Artifact引用，不包含FileReference。"""

    artifact_id: str
    task_id: str
    version: int
    name: str

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id, "artifact_id")
        _validate_id(self.task_id, "task_id")
        if not isinstance(self.version, int) or isinstance(self.version, bool) or self.version < 1:
            raise DeliveryRequestError("artifact version必须从1开始")
        if not isinstance(self.name, str) or not self.name.strip():
            raise DeliveryRequestError("artifact name不能为空")
        object.__setattr__(self, "name", self.name.strip())


@dataclass(frozen=True)
class DeliveryRequest:
    artifact_id: str
    task_id: str
    runtime_context: InvocationContext
    target: DeliveryTarget

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id, "artifact_id")
        _validate_id(self.task_id, "task_id")
        if not isinstance(self.runtime_context, InvocationContext):
            raise DeliveryRequestError("runtime_context无效")
        if not isinstance(self.target, DeliveryTarget):
            raise DeliveryRequestError("target无效")
        if self.task_id != self.runtime_context.task_id:
            raise DeliveryRequestError("Delivery任务与Runtime Context不一致")


@dataclass(frozen=True)
class DeliveryReference:
    delivery_id: str
    artifact_id: str
    external_reference: str
    target_type: DeliveryTargetType

    def __post_init__(self) -> None:
        _validate_id(self.delivery_id, "delivery_id")
        _validate_id(self.artifact_id, "artifact_id")
        if not isinstance(self.external_reference, str) or not self.external_reference.strip():
            raise DeliveryResultError("external_reference不能为空")
        if not isinstance(self.target_type, DeliveryTargetType):
            raise DeliveryResultError("target_type无效")


@dataclass(frozen=True)
class DeliveryResult:
    delivery_id: str
    artifact_id: str
    external_reference: str
    status: DeliveryStatus
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_id(self.delivery_id, "delivery_id")
        _validate_id(self.artifact_id, "artifact_id")
        if not isinstance(self.external_reference, str) or not self.external_reference.strip():
            raise DeliveryResultError("external_reference不能为空")
        if not isinstance(self.status, DeliveryStatus):
            raise DeliveryResultError("delivery status无效")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


def _validate_id(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise DeliveryRequestError(f"{label}格式无效")


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DeliveryRequestError("metadata必须是Mapping")
    frozen: dict[str, Any] = {}
    for key, child in deepcopy(dict(value)).items():
        normalized = str(key).casefold().replace("-", "_")
        if normalized in _SENSITIVE_KEYS:
            raise DeliveryRequestError(f"metadata禁止敏感字段：{key}")
        frozen[str(key)] = _freeze_value(child)
    return MappingProxyType(frozen)


def _freeze_value(value: Any) -> Any:
    if callable(value) or isinstance(value, ModuleType):
        raise DeliveryRequestError("metadata禁止可执行对象")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(child) for child in value)
    raise DeliveryRequestError("metadata仅允许安全基础数据")
