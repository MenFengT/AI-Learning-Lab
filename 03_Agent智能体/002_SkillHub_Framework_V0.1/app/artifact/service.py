"""Artifact生命周期、元数据、文件引用和版本管理。"""

from dataclasses import replace
from typing import Mapping
from uuid import uuid4

from app.runtime.invocation_context import InvocationContext
from app.services.filesystem.models import FileReference
from app.services.filesystem.protocols import FileSystemServiceProtocol

from .errors import (
    ArtifactConflictError,
    ArtifactNotFoundError,
    ArtifactPermissionError,
    ArtifactStateError,
)
from .models import Artifact, ArtifactStatus, ArtifactType
from .protocols import ArtifactIdFactoryProtocol


_ALLOWED_TRANSITIONS: dict[ArtifactStatus, frozenset[ArtifactStatus]] = {
    ArtifactStatus.CREATED: frozenset(
        {ArtifactStatus.PROCESSING, ArtifactStatus.FAILED}
    ),
    ArtifactStatus.PROCESSING: frozenset(
        {ArtifactStatus.COMPLETED, ArtifactStatus.FAILED}
    ),
    ArtifactStatus.COMPLETED: frozenset({ArtifactStatus.ARCHIVED}),
    ArtifactStatus.FAILED: frozenset({ArtifactStatus.ARCHIVED}),
    ArtifactStatus.ARCHIVED: frozenset(),
}


class UUIDArtifactIdFactory:
    """本地稳定格式的产物身份工厂。"""

    def create(self) -> str:
        return f"artifact-{uuid4().hex}"


class ArtifactService:
    """实例级Artifact目录；不读写文件，也不覆盖历史快照。"""

    def __init__(
        self,
        filesystem: FileSystemServiceProtocol,
        id_factory: ArtifactIdFactoryProtocol | None = None,
    ) -> None:
        self._filesystem = filesystem
        self._id_factory = id_factory or UUIDArtifactIdFactory()
        self._versions: dict[str, tuple[Artifact, ...]] = {}

    def create(
        self,
        context: InvocationContext,
        artifact_type: ArtifactType,
        name: str,
        file_reference: FileReference,
        metadata: Mapping[str, object] | None = None,
    ) -> Artifact:
        artifact_id = self._id_factory.create()
        if artifact_id in self._versions:
            raise ArtifactConflictError(f"artifact_id已存在：{artifact_id}")
        artifact = Artifact(
            artifact_id=artifact_id,
            task_id=context.task_id,
            artifact_type=artifact_type,
            name=name,
            file_reference=file_reference,
            version=1,
            status=ArtifactStatus.CREATED,
            metadata=metadata or {},
        )
        self._versions[artifact_id] = (artifact,)
        return artifact

    def get(
        self,
        context: InvocationContext,
        artifact_id: str,
        version: int | None = None,
    ) -> Artifact:
        versions = self._get_versions(artifact_id)
        self._authorize(context, versions[-1])
        if version is None:
            return versions[-1]
        for artifact in versions:
            if artifact.version == version:
                return artifact
        raise ArtifactNotFoundError(
            f"Artifact版本不存在：{artifact_id}@{version}"
        )

    def list_versions(
        self, context: InvocationContext, artifact_id: str
    ) -> tuple[Artifact, ...]:
        versions = self._get_versions(artifact_id)
        self._authorize(context, versions[-1])
        return versions

    def transition(
        self,
        context: InvocationContext,
        artifact_id: str,
        status: ArtifactStatus,
    ) -> Artifact:
        current = self.get(context, artifact_id)
        if status not in _ALLOWED_TRANSITIONS[current.status]:
            raise ArtifactStateError(
                f"非法Artifact状态转换：{current.status.value} -> {status.value}"
            )
        updated = replace(current, status=status)
        versions = self._versions[artifact_id]
        self._versions[artifact_id] = (*versions[:-1], updated)
        return updated

    def create_version(
        self,
        context: InvocationContext,
        artifact_id: str,
        file_reference: FileReference,
        metadata: Mapping[str, object] | None = None,
    ) -> Artifact:
        current = self.get(context, artifact_id)
        if current.status not in {
            ArtifactStatus.COMPLETED,
            ArtifactStatus.FAILED,
            ArtifactStatus.ARCHIVED,
        }:
            raise ArtifactStateError("只有终态产物可以创建新版本")
        if _same_file_content(current.file_reference, file_reference):
            raise ArtifactConflictError("文件内容未变化，禁止创建重复Artifact版本")
        next_artifact = Artifact(
            artifact_id=current.artifact_id,
            task_id=current.task_id,
            artifact_type=current.artifact_type,
            name=current.name,
            file_reference=file_reference,
            version=current.version + 1,
            status=ArtifactStatus.CREATED,
            metadata=metadata if metadata is not None else current.metadata,
        )
        self._versions[artifact_id] = (*self._versions[artifact_id], next_artifact)
        return next_artifact

    def _get_versions(self, artifact_id: str) -> tuple[Artifact, ...]:
        try:
            return self._versions[artifact_id]
        except KeyError as exc:
            raise ArtifactNotFoundError(
                f"Artifact不存在：{artifact_id}"
            ) from exc

    @staticmethod
    def _authorize(context: InvocationContext, artifact: Artifact) -> None:
        if context.task_id != artifact.task_id:
            raise ArtifactPermissionError("不能访问其他任务的Artifact")


def _same_file_content(left: FileReference, right: FileReference) -> bool:
    return (
        left.file_id == right.file_id
        and left.version == right.version
        and left.checksum == right.checksum
    )
