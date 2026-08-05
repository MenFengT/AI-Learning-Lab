"""Planner使用的纯数据模型，不保存任何可执行对象。"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
from types import MappingProxyType, ModuleType
from typing import Any, Mapping


_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SKILL_ID_PATTERN = re.compile(
    r"^[a-z][a-z0-9_-]*/[a-z][a-z0-9_-]*@"
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
_SCHEMA_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_SENSITIVE_KEYS = frozenset(
    {"api_key", "apikey", "authorization", "password", "secret", "token"}
)


class PlanStepStatus(str, Enum):
    """Step状态由Runtime推进；Planner只能产生PENDING。"""

    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class UserRequest:
    """Runtime交给Planner的规范化任务请求。"""

    task_id: str
    user_request: str
    user_id: str | None = None
    inputs: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        _validate_id(self.task_id, "task_id")
        if not isinstance(self.user_request, str) or not self.user_request.strip():
            raise ValueError("user_request不能为空")
        if self.user_id is not None and not self.user_id.strip():
            raise ValueError("user_id不能为空字符串")
        _validate_schema_version(self.schema_version)
        object.__setattr__(self, "inputs", _freeze_mapping(self.inputs, "inputs"))
        object.__setattr__(
            self, "metadata", _freeze_mapping(self.metadata, "metadata")
        )


@dataclass(frozen=True)
class PlanStep:
    """仅引用稳定skill_id的计划步骤。"""

    step_id: str
    order: int
    skill_id: str
    input_schema: Mapping[str, Any]
    dependency: tuple[str, ...]
    expected_output: Mapping[str, Any]
    status: PlanStepStatus = PlanStepStatus.PENDING

    def __post_init__(self) -> None:
        _validate_id(self.step_id, "step_id")
        if not isinstance(self.order, int) or isinstance(self.order, bool):
            raise ValueError("order必须是整数")
        if self.order < 1:
            raise ValueError("order必须从1开始")
        if not isinstance(self.skill_id, str) or not _SKILL_ID_PATTERN.fullmatch(
            self.skill_id
        ):
            raise ValueError("skill_id必须是稳定的namespace/name@version")
        dependencies = tuple(self.dependency)
        for dependency in dependencies:
            _validate_id(dependency, "dependency")
        if len(set(dependencies)) != len(dependencies):
            raise ValueError("dependency不能重复")
        if not isinstance(self.status, PlanStepStatus):
            raise ValueError("status必须是PlanStepStatus")
        object.__setattr__(self, "dependency", dependencies)
        object.__setattr__(
            self,
            "input_schema",
            _freeze_mapping(self.input_schema, "input_schema"),
        )
        object.__setattr__(
            self,
            "expected_output",
            _freeze_mapping(self.expected_output, "expected_output"),
        )


@dataclass(frozen=True)
class TaskPlan:
    """Planner输出的不可变DAG计划快照。"""

    plan_id: str
    task_id: str
    created_at: datetime
    steps: tuple[PlanStep, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        _validate_id(self.plan_id, "plan_id")
        _validate_id(self.task_id, "task_id")
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at必须是datetime")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at必须包含时区")
        steps = tuple(self.steps)
        if any(not isinstance(step, PlanStep) for step in steps):
            raise ValueError("steps只能包含PlanStep")
        _validate_schema_version(self.schema_version)
        object.__setattr__(self, "steps", steps)
        object.__setattr__(
            self, "metadata", _freeze_mapping(self.metadata, "metadata")
        )


def _validate_id(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise ValueError(f"{label}格式无效")


def _validate_schema_version(value: str) -> None:
    if not isinstance(value, str) or not _SCHEMA_VERSION_PATTERN.fullmatch(value):
        raise ValueError("schema_version格式无效")


def _freeze_mapping(value: Mapping[str, Any], location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{location}必须是Mapping")
    frozen: dict[str, Any] = {}
    for key, child in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{location}的键必须是非空字符串")
        if key.casefold().replace("-", "_") in _SENSITIVE_KEYS:
            raise ValueError(f"{location}禁止包含敏感字段：{key}")
        frozen[key] = _freeze_value(child, f"{location}.{key}")
    return MappingProxyType(frozen)


def _freeze_value(value: Any, location: str) -> Any:
    if callable(value) or isinstance(value, ModuleType):
        raise ValueError(f"{location}禁止保存可执行对象")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _freeze_mapping(value, location)
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_value(child, f"{location}[]") for child in value
        )
    if isinstance(value, (set, frozenset)):
        return frozenset(
            _freeze_value(child, f"{location}[]") for child in value
        )
    raise ValueError(f"{location}只允许安全基础数据")
