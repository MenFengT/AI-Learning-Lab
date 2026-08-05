"""FileSystem MCP Server物理Workspace隔离策略。"""

from pathlib import Path
import re


class WorkspacePolicy:
    _AREAS = frozenset({"input", "processing", "output"})
    _TASK = re.compile(r"^[a-zA-Z0-9_-]+$")

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root.resolve()

    @property
    def root(self) -> Path:
        return self._root

    def resolve(self, logical_path: str, task_id: str, *, write: bool = False) -> Path:
        if not self._TASK.fullmatch(task_id):
            raise ValueError("task_id格式无效")
        value = logical_path.replace("\\", "/")
        if value.startswith(("/", "//")) or re.match(r"^[a-zA-Z]:", value):
            raise ValueError("禁止绝对路径或UNC路径")
        if value.casefold().startswith("file://") or "://" in value:
            raise ValueError("禁止URI路径")
        parts = value.split("/")
        if len(parts) < 2 or parts[0] not in self._AREAS:
            raise ValueError("路径区域无效")
        if any(part in {"", ".", ".."} for part in parts):
            raise ValueError("路径包含非法目录片段")
        if write and parts[0] == "input":
            raise PermissionError("input区域只读")
        task_root = (self._root / parts[0] / task_id).resolve()
        task_root.mkdir(parents=True, exist_ok=True)
        candidate = (task_root.joinpath(*parts[1:])).resolve(strict=False)
        try:
            candidate.relative_to(task_root)
        except ValueError as exc:
            raise ValueError("路径或符号链接超出任务Workspace") from exc
        return candidate
