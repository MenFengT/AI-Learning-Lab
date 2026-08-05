"""Office Service输入输出契约，不包含OfficeCLI对象或本地路径。"""

from copy import deepcopy
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Mapping

from app.runtime.invocation_context import InvocationContext
from app.services.filesystem.models import FileReference


class _ImmutableMapping(Mapping[str, Any]):
    def __init__(self, value: Mapping[str, Any]) -> None:
        self._value = {
            key: _freeze_value(child)
            for key, child in deepcopy(dict(value)).items()
        }

    def __getitem__(self, key: str) -> Any:
        return self._value[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._value)

    def __len__(self) -> int:
        return len(self._value)

    def __deepcopy__(self, memo: dict[int, Any]) -> "_ImmutableMapping":
        return _ImmutableMapping(deepcopy(self._value, memo))


@dataclass(frozen=True)
class OfficeDocumentRequest:
    runtime_context: InvocationContext
    output_name: str
    content: Mapping[str, Any] = field(default_factory=dict)
    source_file_id: str | None = None
    source_version: str | None = None
    target_format: str | None = None
    idempotency_key: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    timeout: float = 30.0

    def __post_init__(self) -> None:
        if not self.output_name.strip():
            raise ValueError("output_name不能为空")
        if any(marker in self.output_name for marker in ("/", "\\", ":")):
            raise ValueError("output_name只能是文件名，不能包含路径")
        if (self.source_file_id is None) != (self.source_version is None):
            raise ValueError("source_file_id与source_version必须同时提供")
        if self.timeout <= 0:
            raise ValueError("timeout必须大于0")
        object.__setattr__(self, "content", _freeze(self.content))
        object.__setattr__(self, "metadata", _freeze(self.metadata))


@dataclass(frozen=True)
class OfficeDocumentResult:
    file_reference: FileReference
    format: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.file_reference, FileReference):
            raise ValueError("file_reference必须为FileReference")
        if not self.format.strip():
            raise ValueError("format不能为空")
        object.__setattr__(self, "metadata", _freeze(self.metadata))


def _freeze(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return _ImmutableMapping(value)


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(child) for child in value)
    return value


def to_plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): to_plain(child) for key, child in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(to_plain(child) for child in value)
    return value
