"""FileSystem MCP原子Tool实现，不包含业务分类或整理规则。"""

from datetime import datetime, timedelta, timezone
import hashlib
import mimetypes
from pathlib import Path
import shutil
from typing import Any, Callable, Mapping
from uuid import uuid4
import zipfile

from .identity_store import (
    FileIdentity,
    FileIdentityStoreProtocol,
    InMemoryFileIdentityStore,
)
from .models import PendingDelete
from .workspace_policy import WorkspacePolicy


class UnsupportedFileTypeError(ValueError):
    pass


class DeleteConfirmationError(PermissionError):
    pass


class FileSystemTools:
    def __init__(
        self,
        policy: WorkspacePolicy,
        *,
        max_file_size: int,
        confirmation_ttl_seconds: float = 300.0,
        now: Callable[[], datetime] | None = None,
        identity_store: FileIdentityStoreProtocol | None = None,
    ) -> None:
        if max_file_size <= 0 or confirmation_ttl_seconds <= 0:
            raise ValueError("文件限制和确认有效期必须大于0")
        self._policy = policy
        self._max_file_size = max_file_size
        self._confirmation_ttl = confirmation_ttl_seconds
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._identity_store = identity_store or InMemoryFileIdentityStore()
        self._pending_deletes: dict[str, PendingDelete] = {}

    def list_files(self, args: Mapping[str, Any], task_id: str) -> Mapping[str, Any]:
        directory = self._policy.resolve(self._required(args, "source"), task_id)
        if not directory.exists() or not directory.is_dir():
            raise FileNotFoundError("目录不存在")
        files = [self._reference(path, task_id) for path in sorted(directory.iterdir()) if path.is_file()]
        return {"files": files}

    def read_file(self, args: Mapping[str, Any], task_id: str) -> Mapping[str, Any]:
        path = self._existing_file(self._required(args, "source"), task_id)
        self._check_size(path.stat().st_size)
        return {"file": self._reference(path, task_id), "content": path.read_bytes()}

    def write_file(self, args: Mapping[str, Any], task_id: str) -> Mapping[str, Any]:
        logical = self._required(args, "target")
        path = self._policy.resolve(logical, task_id, write=True)
        content = args.get("content")
        if not isinstance(content, bytes):
            raise TypeError("write content必须是bytes")
        self._check_size(len(content))
        overwrite = bool(args.get("overwrite", False))
        if path.exists() and not overwrite:
            raise FileExistsError("目标文件已存在")
        expected = args.get("expected_version")
        if path.exists() and expected is not None:
            current = self._identity(path).version
            if str(current) != str(expected):
                raise ValueError("文件version不匹配")
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            temp.write_bytes(content)
            temp.replace(path)
        finally:
            if temp.exists():
                temp.unlink()
        key = str(path)
        current = self._identity_store.get(key)
        self._identity_store.save(
            key,
            FileIdentity(
                file_id=current.file_id if current else uuid4().hex,
                version=current.version + 1 if current else 1,
                checksum=self._checksum(path),
                source_file_id=current.source_file_id if current else None,
            ),
        )
        return {"file": self._reference(path, task_id)}

    def copy_file(self, args: Mapping[str, Any], task_id: str) -> Mapping[str, Any]:
        source = self._existing_file(self._required(args, "source"), task_id)
        target = self._target(args, task_id)
        self._prepare_target(target, bool(args.get("overwrite", False)))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        source_id = self._identity(source).file_id
        self._identity_store.save(
            str(target),
            FileIdentity(
                uuid4().hex, 1, self._checksum(target), source_id
            ),
        )
        return {"file": self._reference(target, task_id)}

    def move_file(self, args: Mapping[str, Any], task_id: str) -> Mapping[str, Any]:
        source = self._existing_file(self._required(args, "source"), task_id)
        target = self._target(args, task_id)
        self._prepare_target(target, bool(args.get("overwrite", False)))
        self._identity(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        self._identity_store.move(str(source), str(target))
        return {"file": self._reference(target, task_id)}

    def rename_file(self, args: Mapping[str, Any], task_id: str) -> Mapping[str, Any]:
        return self.move_file(args, task_id)

    def archive(self, args: Mapping[str, Any], task_id: str) -> Mapping[str, Any]:
        action = args.get("archive_action")
        if action == "create":
            return self._create_archive(args, task_id)
        if action == "extract":
            return self._extract_archive(args, task_id)
        raise UnsupportedFileTypeError("archive_action必须为create或extract")

    def request_delete(self, args: Mapping[str, Any], task_id: str) -> Mapping[str, Any]:
        logical = self._required(args, "path")
        path = self._existing_file(logical, task_id)
        reference = self._reference(path, task_id)
        if reference["version"] != str(args.get("expected_version")) or reference["checksum"] != args.get("expected_checksum"):
            raise ValueError("删除目标version或checksum不匹配")
        confirmation_id = uuid4().hex
        pending = PendingDelete(
            confirmation_id=confirmation_id,
            task_id=task_id,
            logical_path=logical,
            file_id=reference["file_id"],
            version=reference["version"],
            checksum=reference["checksum"],
            expire_time=self._now() + timedelta(seconds=self._confirmation_ttl),
        )
        self._pending_deletes[confirmation_id] = pending
        return {"confirmation_id": confirmation_id, "file_id": pending.file_id, "version": pending.version, "checksum": pending.checksum, "expire_time": pending.expire_time.isoformat()}

    def confirm_delete(self, args: Mapping[str, Any], task_id: str) -> Mapping[str, Any]:
        confirmation_id = self._required(args, "confirmation_id")
        pending = self._pending_deletes.pop(confirmation_id, None)
        if pending is None or pending.task_id != task_id:
            raise DeleteConfirmationError("删除确认不存在或不属于当前任务")
        if self._now() > pending.expire_time:
            raise DeleteConfirmationError("删除确认已过期")
        if pending.logical_path != self._required(args, "path"):
            raise DeleteConfirmationError("删除目标已变化")
        path = self._existing_file(pending.logical_path, task_id)
        reference = self._reference(path, task_id)
        if reference["file_id"] != pending.file_id or reference["version"] != str(args.get("expected_version")) or reference["checksum"] != args.get("expected_checksum") or reference["checksum"] != pending.checksum:
            raise DeleteConfirmationError("删除确认的身份、version或checksum无效")
        trash = self._policy.root / ".trash" / task_id
        trash.mkdir(parents=True, exist_ok=True)
        target = trash / f"{confirmation_id}-{path.name}"
        shutil.move(str(path), str(target))
        self._identity_store.remove(str(path))
        return {"file": reference}

    def _create_archive(self, args: Mapping[str, Any], task_id: str) -> Mapping[str, Any]:
        sources = args.get("sources")
        if not isinstance(sources, (list, tuple)) or not sources:
            raise ValueError("归档sources不能为空")
        paths = [self._existing_file(str(item), task_id) for item in sources]
        target = self._target(args, task_id)
        if target.suffix.casefold() != ".zip":
            raise UnsupportedFileTypeError("V0.2只支持ZIP")
        self._prepare_target(target, bool(args.get("overwrite", False)))
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in paths:
                archive.write(path, arcname=path.name)
        self._check_size(target.stat().st_size)
        self._identity_store.save(
            str(target),
            FileIdentity(uuid4().hex, 1, self._checksum(target)),
        )
        return {"file": self._reference(target, task_id)}

    def _extract_archive(self, args: Mapping[str, Any], task_id: str) -> Mapping[str, Any]:
        source = self._existing_file(self._required(args, "source"), task_id)
        target = self._policy.resolve(self._required(args, "target"), task_id, write=True)
        if source.suffix.casefold() != ".zip":
            raise UnsupportedFileTypeError("V0.2只支持ZIP")
        overwrite = bool(args.get("overwrite", False))
        if target.exists() and not overwrite:
            raise FileExistsError("解压目标已存在")
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = target.parent / f".{target.name}.{uuid4().hex}.extracting"
        extracted_relative: list[Path] = []
        with zipfile.ZipFile(source, "r") as archive:
            infos = archive.infolist()
            if len(infos) > 1000:
                raise ValueError("归档文件数量超限")
            total_size = 0
            for info in infos:
                total_size += info.file_size
                self._check_size(total_size)
                if info.flag_bits & 0x1:
                    raise ValueError("禁止加密归档条目")
                file_type = (info.external_attr >> 16) & 0o170000
                if file_type == 0o120000:
                    raise ValueError("禁止归档符号链接")
                destination = (staging / info.filename).resolve(strict=False)
                try:
                    destination.relative_to(staging.resolve())
                except ValueError as exc:
                    raise ValueError("归档条目路径越界") from exc
            staging.mkdir()
            try:
                for info in infos:
                    destination = (staging / info.filename).resolve(strict=False)
                    if info.is_dir():
                        destination.mkdir(parents=True, exist_ok=True)
                        continue
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info, "r") as source_stream, destination.open("wb") as output:
                        shutil.copyfileobj(source_stream, output)
                    extracted_relative.append(destination.relative_to(staging))
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                staging.replace(target)
            except Exception:
                if staging.exists():
                    shutil.rmtree(staging)
                raise
        extracted = []
        for relative in extracted_relative:
            destination = target / relative
            self._identity_store.save(
                str(destination),
                FileIdentity(uuid4().hex, 1, self._checksum(destination)),
            )
            extracted.append(self._reference(destination, task_id))
        return {"files": extracted}

    def _existing_file(self, logical: str, task_id: str) -> Path:
        path = self._policy.resolve(logical, task_id)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError("文件不存在")
        return path

    def _target(self, args: Mapping[str, Any], task_id: str) -> Path:
        return self._policy.resolve(self._required(args, "target"), task_id, write=True)

    @staticmethod
    def _prepare_target(path: Path, overwrite: bool) -> None:
        if path.exists() and not overwrite:
            raise FileExistsError("目标已存在")
        if path.exists() and path.is_dir():
            raise IsADirectoryError("目标是目录")

    def _identity(self, path: Path) -> FileIdentity:
        key = str(path)
        checksum = self._checksum(path)
        identity = self._identity_store.get(key)
        if identity is None:
            identity = FileIdentity(uuid4().hex, 1, checksum)
            self._identity_store.save(key, identity)
        elif identity.checksum != checksum:
            identity = FileIdentity(
                identity.file_id,
                identity.version + 1,
                checksum,
                identity.source_file_id,
            )
            self._identity_store.save(key, identity)
        return identity

    def _reference(self, path: Path, task_id: str) -> Mapping[str, Any]:
        stat = path.stat()
        identity = self._identity(path)
        relative = self._logical_path(path, task_id)
        created = datetime.fromtimestamp(stat.st_ctime, timezone.utc)
        updated = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
        return {"file_id": identity.file_id, "version": str(identity.version), "checksum": identity.checksum, "area": relative.split("/", 1)[0], "relative_path": relative, "created_at": created.isoformat(), "updated_at": updated.isoformat(), "source_file_id": identity.source_file_id, "metadata": {"size": stat.st_size, "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream", "metadata": {}}}

    def _logical_path(self, path: Path, task_id: str) -> str:
        for area in ("input", "processing", "output"):
            root = (self._policy.root / area / task_id).resolve()
            try:
                relative = path.resolve().relative_to(root)
                return f"{area}/{relative.as_posix()}"
            except ValueError:
                continue
        raise ValueError("文件不属于当前任务Workspace")

    @staticmethod
    def _checksum(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _check_size(self, size: int) -> None:
        if size > self._max_file_size:
            raise OverflowError("文件大小超限")

    @staticmethod
    def _required(args: Mapping[str, Any], key: str) -> str:
        value = args.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"缺少字段：{key}")
        return value
