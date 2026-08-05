import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

from app.artifact import Artifact, ArtifactStatus, ArtifactType
from app.services.filesystem.models import (
    FileMetadata,
    FileReference,
    WorkspaceArea,
)


def file_reference(version: str = "1", checksum: str = "checksum-1") -> FileReference:
    now = datetime.now(timezone.utc)
    return FileReference(
        file_id="file-001",
        version=version,
        checksum=checksum,
        area=WorkspaceArea.OUTPUT,
        relative_path="task-001/result.docx",
        metadata=FileMetadata(10, "application/octet-stream", now, now),
        created_at=now,
        updated_at=now,
    )


class ArtifactModelTests(unittest.TestCase):
    def test_required_contract_and_immutability(self) -> None:
        source_metadata = {"source": {"pages": [1, 2]}}
        artifact = Artifact(
            artifact_id="artifact-001",
            task_id="task-001",
            artifact_type=ArtifactType.DOCUMENT,
            name="成果.docx",
            file_reference=file_reference(),
            version=1,
            status=ArtifactStatus.CREATED,
            metadata=source_metadata,
        )
        source_metadata["source"]["pages"].append(3)

        self.assertEqual(artifact.metadata["source"]["pages"], (1, 2))
        with self.assertRaises(FrozenInstanceError):
            artifact.version = 2  # type: ignore[misc]

    def test_invalid_version_and_sensitive_metadata_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Artifact(
                "artifact-001",
                "task-001",
                ArtifactType.GENERIC,
                "result",
                file_reference(),
                0,
                ArtifactStatus.CREATED,
            )
        with self.assertRaises(ValueError):
            Artifact(
                "artifact-001",
                "task-001",
                ArtifactType.GENERIC,
                "result",
                file_reference(),
                1,
                ArtifactStatus.CREATED,
                {"token": "sensitive"},
            )


if __name__ == "__main__":
    unittest.main()
