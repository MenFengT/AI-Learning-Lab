import unittest

from app.artifact import (
    ArtifactPermissionError,
    ArtifactService,
    ArtifactStateError,
    ArtifactStatus,
    ArtifactType,
)
from app.runtime.invocation_context import InvocationContext

from .test_artifact_models import file_reference


class FixedIdFactory:
    def create(self) -> str:
        return "artifact-001"


class FileSystemMustNotBeCalled:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"Artifact不得执行文件操作：{name}")


def context(task_id: str = "task-001") -> InvocationContext:
    return InvocationContext(
        task_id=task_id,
        trace_id="trace-001",
        span_id="span-001",
        skill_id="local/probe@0.3.0",
    )


class ArtifactServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ArtifactService(FileSystemMustNotBeCalled(), FixedIdFactory())

    def test_lifecycle_and_file_reference_management(self) -> None:
        artifact = self.service.create(
            context(),
            ArtifactType.DOCUMENT,
            "成果.docx",
            file_reference(),
            {"purpose": "交付"},
        )
        processing = self.service.transition(
            context(), artifact.artifact_id, ArtifactStatus.PROCESSING
        )
        completed = self.service.transition(
            context(), artifact.artifact_id, ArtifactStatus.COMPLETED
        )
        archived = self.service.transition(
            context(), artifact.artifact_id, ArtifactStatus.ARCHIVED
        )

        self.assertEqual(processing.status, ArtifactStatus.PROCESSING)
        self.assertEqual(completed.status, ArtifactStatus.COMPLETED)
        self.assertEqual(archived.status, ArtifactStatus.ARCHIVED)
        self.assertIs(archived.file_reference, artifact.file_reference)

    def test_invalid_transition_and_cross_task_access_are_rejected(self) -> None:
        artifact = self.service.create(
            context(), ArtifactType.GENERIC, "result", file_reference()
        )
        with self.assertRaises(ArtifactStateError):
            self.service.transition(
                context(), artifact.artifact_id, ArtifactStatus.COMPLETED
            )
        with self.assertRaises(ArtifactPermissionError):
            self.service.get(context("task-002"), artifact.artifact_id)


if __name__ == "__main__":
    unittest.main()
