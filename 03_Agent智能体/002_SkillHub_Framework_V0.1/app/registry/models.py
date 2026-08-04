"""Skill Registry的强类型数据契约。"""

from dataclasses import dataclass, field, replace
from enum import Enum
import re
from typing import Any


_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
_VERSION_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
_MANIFEST_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?$")
_SCHEMA_TYPES = frozenset(
    {"string", "integer", "number", "boolean", "object", "array", "null"}
)


class SkillLifecycleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


class HealthStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


@dataclass(frozen=True)
class SchemaField:
    name: str
    type: str
    required: bool
    description: str
    default: Any | None = None

    def __post_init__(self) -> None:
        _validate_identifier(self.name, "schema field name")
        if self.type not in _SCHEMA_TYPES:
            raise ValueError(f"不支持的Schema字段类型：{self.type}")
        if not self.description.strip():
            raise ValueError("Schema字段description不能为空")
        if self.required and self.default is not None:
            raise ValueError("必填Schema字段不能声明default")


@dataclass(frozen=True)
class SkillMetadata:
    name: str
    version: str
    description: str
    inputs: tuple[SchemaField, ...]
    outputs: tuple[SchemaField, ...]
    permissions: frozenset[str] = field(default_factory=frozenset)
    keywords: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_identifier(self.name, "skill name")
        validate_version(self.version)
        if not self.description.strip():
            raise ValueError("Skill description不能为空")
        _validate_schema_fields(self.inputs, "inputs")
        _validate_schema_fields(self.outputs, "outputs")
        if any(not permission.strip() for permission in self.permissions):
            raise ValueError("Skill permission不能为空")
        normalized_keywords = tuple(keyword.strip() for keyword in self.keywords)
        if any(not keyword for keyword in normalized_keywords):
            raise ValueError("Skill keyword不能为空")
        if len(set(keyword.casefold() for keyword in normalized_keywords)) != len(
            normalized_keywords
        ):
            raise ValueError("Skill keywords不能重复")


@dataclass(frozen=True)
class SkillRegistration:
    skill_id: str
    namespace: str
    name: str
    version: str
    manifest_version: str
    metadata: SkillMetadata
    lifecycle_status: SkillLifecycleStatus
    health_status: HealthStatus = HealthStatus.UNKNOWN

    def __post_init__(self) -> None:
        _validate_identifier(self.namespace, "namespace")
        _validate_identifier(self.name, "skill name")
        validate_version(self.version)
        if not _MANIFEST_VERSION_PATTERN.fullmatch(self.manifest_version):
            raise ValueError(
                f"manifest_version格式无效：{self.manifest_version}"
            )
        expected_id = build_skill_id(self.namespace, self.name, self.version)
        if self.skill_id != expected_id:
            raise ValueError(f"skill_id必须为：{expected_id}")
        if self.metadata.name != self.name or self.metadata.version != self.version:
            raise ValueError("Registration与Metadata的name/version不一致")

    def with_health(self, status: HealthStatus) -> "SkillRegistration":
        return replace(self, health_status=status)


@dataclass(frozen=True)
class HealthCheckResult:
    status: HealthStatus
    messages: tuple[str, ...] = ()


def build_skill_id(namespace: str, name: str, version: str) -> str:
    _validate_identifier(namespace, "namespace")
    _validate_identifier(name, "skill name")
    validate_version(version)
    return f"{namespace}/{name}@{version}"


def validate_version(version: str) -> None:
    if not _VERSION_PATTERN.fullmatch(version):
        raise ValueError(f"版本必须符合语义化版本格式：{version}")


def _validate_identifier(value: str, label: str) -> None:
    if not _IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"{label}格式无效：{value}")


def _validate_schema_fields(fields: tuple[SchemaField, ...], label: str) -> None:
    names = [item.name for item in fields]
    if len(set(names)) != len(names):
        raise ValueError(f"{label}字段名不能重复")
