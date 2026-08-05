"""Artifact Layer 公共协议。"""

from typing import Mapping, Protocol

from app.runtime.invocation_context import InvocationContext
from app.services.filesystem.models import FileReference

from .models import Artifact, ArtifactStatus, ArtifactType


class ArtifactServiceProtocol(Protocol):
    def create(
        self,
        context: InvocationContext,
        artifact_type: ArtifactType,
        name: str,
        file_reference: FileReference,
        metadata: Mapping[str, object] | None = None,
    ) -> Artifact: ...

    def get(
        self,
        context: InvocationContext,
        artifact_id: str,
        version: int | None = None,
    ) -> Artifact: ...

    def list_versions(
        self, context: InvocationContext, artifact_id: str
    ) -> tuple[Artifact, ...]: ...

    def transition(
        self,
        context: InvocationContext,
        artifact_id: str,
        status: ArtifactStatus,
    ) -> Artifact: ...

    def create_version(
        self,
        context: InvocationContext,
        artifact_id: str,
        file_reference: FileReference,
        metadata: Mapping[str, object] | None = None,
    ) -> Artifact: ...


class ArtifactIdFactoryProtocol(Protocol):
    def create(self) -> str: ...
