"""任务产物的不可变数据契约。"""

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
import re
from types import MappingProxyType, ModuleType
from typing import Any, Mapping

from app.services.filesystem.models import FileReference


_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SENSITIVE_KEYS = frozenset(
    {"api_key", "apikey", "authorization", "password", "secret", "token"}
)


class ArtifactType(str, Enum):
    DOCUMENT = "DOCUMENT"
    SPREADSHEET = "SPREADSHEET"
    PRESENTATION = "PRESENTATION"
    ARCHIVE = "ARCHIVE"
    GENERIC = "GENERIC"


class ArtifactStatus(str, Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class Artifact:
    """一个产物版本快照；历史版本创建后不可覆盖。"""

    artifact_id: str
    task_id: str
    artifact_type: ArtifactType
    name: str
    file_reference: FileReference
    version: int
    status: ArtifactStatus
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id, "artifact_id")
        _validate_id(self.task_id, "task_id")
        if not isinstance(self.artifact_type, ArtifactType):
            raise ValueError("artifact_type必须为ArtifactType")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name不能为空")
        if not isinstance(self.file_reference, FileReference):
            raise ValueError("file_reference必须为FileReference")
        if not isinstance(self.version, int) or isinstance(self.version, bool):
            raise ValueError("version必须为整数")
        if self.version < 1:
            raise ValueError("version必须从1开始")
        if not isinstance(self.status, ArtifactStatus):
            raise ValueError("status必须为ArtifactStatus")
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


def _validate_id(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise ValueError(f"{label}格式无效")


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("metadata必须为Mapping")
    frozen: dict[str, Any] = {}
    for key, child in deepcopy(dict(value)).items():
        if not isinstance(key, str) or not key:
            raise ValueError("metadata键必须为非空字符串")
        if key.casefold().replace("-", "_") in _SENSITIVE_KEYS:
            raise ValueError(f"metadata禁止包含敏感字段：{key}")
        frozen[key] = _freeze_value(child)
    return MappingProxyType(frozen)


def _freeze_value(value: Any) -> Any:
    if callable(value) or isinstance(value, ModuleType):
        raise ValueError("metadata禁止保存可执行对象")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(child) for child in value)
    raise ValueError("metadata只允许安全基础数据")
