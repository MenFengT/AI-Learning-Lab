import unittest

from app.artifact import (
    ArtifactConflictError,
    ArtifactService,
    ArtifactStatus,
    ArtifactType,
)

from .test_artifact_models import file_reference
from .test_artifact_service import FileSystemMustNotBeCalled, FixedIdFactory, context


class ArtifactVersionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ArtifactService(FileSystemMustNotBeCalled(), FixedIdFactory())
        artifact = self.service.create(
            context(), ArtifactType.DOCUMENT, "成果.docx", file_reference()
        )
        self.service.transition(
            context(), artifact.artifact_id, ArtifactStatus.PROCESSING
        )
        self.v1 = self.service.transition(
            context(), artifact.artifact_id, ArtifactStatus.COMPLETED
        )

    def test_content_change_creates_new_version_and_preserves_history(self) -> None:
        v2 = self.service.create_version(
            context(),
            self.v1.artifact_id,
            file_reference("2", "checksum-2"),
        )

        self.assertEqual(v2.version, 2)
        self.assertEqual(v2.status, ArtifactStatus.CREATED)
        versions = self.service.list_versions(context(), self.v1.artifact_id)
        self.assertEqual([item.version for item in versions], [1, 2])
        self.assertEqual(versions[0].file_reference.checksum, "checksum-1")
        self.assertEqual(
            self.service.get(context(), self.v1.artifact_id, 1),
            self.v1,
        )

    def test_unchanged_content_cannot_create_duplicate_version(self) -> None:
        with self.assertRaises(ArtifactConflictError):
            self.service.create_version(
                context(), self.v1.artifact_id, file_reference()
            )


if __name__ == "__main__":
    unittest.main()
