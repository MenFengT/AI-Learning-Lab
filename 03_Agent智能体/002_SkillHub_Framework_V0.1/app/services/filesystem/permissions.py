"""FileSystem Service权限与逻辑Workspace路径策略。"""

from enum import Enum
import re
from types import MappingProxyType
from typing import Mapping


class FilePermission(str, Enum):
    LIST = "FILE_LIST"
    READ = "FILE_READ"
    WRITE = "FILE_WRITE"
    COPY = "FILE_COPY"
    MOVE = "FILE_MOVE"
    RENAME = "FILE_RENAME"
    DELETE = "FILE_DELETE"
    ARCHIVE = "FILE_ARCHIVE"


class FileSystemAccessPolicy:
    def __init__(
        self, grants: Mapping[str, frozenset[FilePermission]]
    ) -> None:
        self._grants = MappingProxyType(dict(grants))

    def allows(self, skill_id: str, permission: FilePermission) -> bool:
        return permission in self._grants.get(skill_id, frozenset())


class WorkspacePolicy:
    """Service侧只校验逻辑路径；真实路径由MCP Server再次校验。"""

    _DRIVE = re.compile(r"^[a-zA-Z]:")
    _TASK_ID = re.compile(r"^[a-zA-Z0-9_-]+$")
    _AREAS = frozenset({"input", "processing", "output"})

    def validate_path(self, path: str) -> str:
        value = path.strip().replace("\\", "/")
        lowered = value.casefold()
        if not value or "\x00" in value:
            raise ValueError("文件路径不能为空或包含空字节")
        if value.startswith(("/", "//")) or self._DRIVE.match(value):
            raise ValueError("禁止绝对路径或UNC路径")
        if lowered.startswith("file://") or "://" in lowered:
            raise ValueError("禁止URI路径")
        parts = value.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise ValueError("文件路径包含非法目录片段")
        if parts[0] not in self._AREAS or len(parts) < 2:
            raise ValueError("路径必须位于input、processing或output区域内")
        if ":" in value or "*" in value or "?" in value:
            raise ValueError("文件路径包含禁止字符")
        return "/".join(parts)

    def validate_task_id(self, task_id: str) -> str:
        if not self._TASK_ID.fullmatch(task_id):
            raise ValueError("task_id格式无效")
        return task_id
