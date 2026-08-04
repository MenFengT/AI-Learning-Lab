"""FileSystem Service稳定数据契约。"""

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections.abc import Iterator
from typing import Any, Mapping

from app.runtime.invocation_context import InvocationContext


class _ImmutableMapping(Mapping[str, Any]):
    def __init__(self, value: Mapping[str, Any]) -> None:
        self._value = deepcopy(dict(value))

    def __getitem__(self, key: str) -> Any:
        return self._value[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._value)

    def __len__(self) -> int:
        return len(self._value)

    def __deepcopy__(self, memo: dict[int, Any]) -> "_ImmutableMapping":
        return _ImmutableMapping(deepcopy(self._value, memo))


class WorkspaceArea(str, Enum):
    INPUT = "input"
    PROCESSING = "processing"
    OUTPUT = "output"


@dataclass(frozen=True)
class FileSystemRuntimeContext(InvocationContext):
    """FileSystem旧上下文名称的兼容类型。"""


@dataclass(frozen=True)
class FileMetadata:
    size: int
    content_type: str
    created_at: datetime
    updated_at: datetime
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.size < 0:
            raise ValueError("size不能小于0")
        object.__setattr__(self, "metadata", _ImmutableMapping(self.metadata))


@dataclass(frozen=True)
class FileReference:
    file_id: str
    version: str
    checksum: str
    area: WorkspaceArea
    relative_path: str
    metadata: FileMetadata
    created_at: datetime
    updated_at: datetime
    source_file_id: str | None = None


@dataclass(frozen=True)
class FileOperationRequest:
    runtime_context: FileSystemRuntimeContext
    source: str | None = None
    target: str | None = None
    content: bytes | None = None
    sources: tuple[str, ...] = ()
    expected_version: str | None = None
    overwrite: bool = False
    archive_action: str | None = None
    timeout: float = 10.0

    def __post_init__(self) -> None:
        if self.timeout <= 0:
            raise ValueError("timeout必须大于0")
        object.__setattr__(self, "content", deepcopy(self.content))


@dataclass(frozen=True)
class FileOperationResult:
    operation: str
    file: FileReference | None = None
    files: tuple[FileReference, ...] = ()
    content: bytes | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "content", deepcopy(self.content))


@dataclass(frozen=True)
class DeleteRequest:
    runtime_context: FileSystemRuntimeContext
    path: str
    expected_version: str
    expected_checksum: str
    confirmation_id: str | None = None
    timeout: float = 10.0


@dataclass(frozen=True)
class DeleteConfirmation:
    confirmation_id: str
    file_id: str
    version: str
    checksum: str
    expire_time: datetime


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class TaskProgress:
    completed: int
    total: int
    message: str = ""


@dataclass(frozen=True)
class BatchFileTask:
    task_id: str
    status: TaskStatus
    progress: TaskProgress
