"""真实OfficeCLI输出的本地工作区解析实现。"""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from app.mcp_servers.office.runtime.errors import OfficeCLIResponseError
from app.mcp_servers.office.runtime.models import OfficeCLIRequest
from app.services.filesystem.models import FileMetadata, FileReference, WorkspaceArea


@dataclass(frozen=True)
class LocalOfficeCLIOutputResolver:
    """仅访问由task_id和文件名推导的workspace/output路径。"""

    application_root: Path

    def prepare(self, request: OfficeCLIRequest) -> None:
        self._task_directory(request).mkdir(parents=True, exist_ok=True)

    def resolve(self, request: OfficeCLIRequest) -> FileReference:
        target = self._target(request)
        if not target.is_file() or target.is_symlink():
            raise OfficeCLIResponseError("OfficeCLI未生成受控输出文件")
        payload = target.read_bytes()
        if not payload:
            raise OfficeCLIResponseError("OfficeCLI生成了空文件")
        timestamp = datetime.fromtimestamp(target.stat().st_mtime, timezone.utc)
        checksum = sha256(payload).hexdigest()
        output_name = self._output_name(request)
        return FileReference(
            file_id=f"office-{sha256(f'{request.task_id}/{output_name}'.encode()).hexdigest()[:24]}",
            version="1",
            checksum=checksum,
            area=WorkspaceArea.OUTPUT,
            relative_path=f"output/{request.task_id}/{output_name}",
            metadata=FileMetadata(
                size=len(payload),
                content_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
                created_at=timestamp,
                updated_at=timestamp,
                metadata={"producer": "officecli-mcp", "verified": True},
            ),
            created_at=timestamp,
            updated_at=timestamp,
        )

    def _target(self, request: OfficeCLIRequest) -> Path:
        directory = self._task_directory(request)
        target = (directory / self._output_name(request)).resolve()
        if target.parent != directory:
            raise OfficeCLIResponseError("OfficeCLI输出路径越界")
        return target

    def _task_directory(self, request: OfficeCLIRequest) -> Path:
        root = (self.application_root / "workspace" / "output").resolve()
        directory = (root / request.task_id).resolve()
        if directory.parent != root:
            raise OfficeCLIResponseError("OfficeCLI任务目录越界")
        return directory

    @staticmethod
    def _output_name(request: OfficeCLIRequest) -> str:
        value = request.arguments.get("output_name")
        if not isinstance(value, str) or not value.strip():
            raise OfficeCLIResponseError("OfficeCLI输出文件名缺失")
        if any(marker in value for marker in ("/", "\\", ":", "..")):
            raise OfficeCLIResponseError("OfficeCLI输出文件名不安全")
        return value
