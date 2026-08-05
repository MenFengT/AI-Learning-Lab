from io import BytesIO
import tempfile
import unittest
from pathlib import Path
import zipfile

from app.services.filesystem import DeleteRequest, FileOperationRequest, FileSystemRuntimeContext

from .helpers import SKILL_ID, build_service


def runtime() -> FileSystemRuntimeContext:
    return FileSystemRuntimeContext("task-001", "trace-001", "span-001", SKILL_ID)


class DeleteAndArchiveTests(unittest.TestCase):
    def test_two_phase_delete_checks_version_checksum_and_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service, audit, _ = build_service(root)
            created = service.write_file(FileOperationRequest(runtime(), target="processing/delete.txt", content=b"delete me"))
            reference = created.data.file
            confirmation = service.request_delete(DeleteRequest(runtime(), "processing/delete.txt", reference.version, reference.checksum))
            wrong = service.confirm_delete(DeleteRequest(runtime(), "processing/delete.txt", reference.version, "wrong", confirmation.data.confirmation_id))

            confirmation2 = service.request_delete(DeleteRequest(runtime(), "processing/delete.txt", reference.version, reference.checksum))
            deleted = service.confirm_delete(DeleteRequest(runtime(), "processing/delete.txt", reference.version, reference.checksum, confirmation2.data.confirmation_id))
            source_exists = (root / "processing" / "task-001" / "delete.txt").exists()
            trash_exists = (root / ".trash" / "task-001").exists()

        self.assertTrue(confirmation.success)
        self.assertFalse(wrong.success)
        self.assertTrue(deleted.success)
        self.assertFalse(source_exists)
        self.assertTrue(trash_exists)
        self.assertTrue(
            any(
                event.metadata.get("operation_name") == "confirm_delete"
                for event in audit.events()
            )
        )

    def test_archive_create_and_extract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _, _ = build_service(Path(directory))
            service.write_file(FileOperationRequest(runtime(), target="processing/a.txt", content=b"a"))
            archived = service.archive_file(FileOperationRequest(runtime(), sources=("processing/a.txt",), target="output/files.zip", archive_action="create"))
            extracted = service.archive_file(FileOperationRequest(runtime(), source="output/files.zip", target="processing/unpacked", archive_action="extract"))

        self.assertTrue(archived.success)
        self.assertEqual(archived.data.file.relative_path, "output/files.zip")
        self.assertTrue(extracted.success)
        self.assertEqual(extracted.data.files[0].relative_path, "processing/unpacked/a.txt")

    def test_archive_rejects_path_traversal_entry(self) -> None:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("../escape.txt", "unsafe")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service, _, _ = build_service(root)
            service.write_file(FileOperationRequest(runtime(), target="processing/evil.zip", content=buffer.getvalue()))
            result = service.archive_file(FileOperationRequest(runtime(), source="processing/evil.zip", target="processing/unpacked", archive_action="extract"))
            leaked = (root / "processing" / "task-001" / "escape.txt").exists()

        self.assertFalse(result.success)
        self.assertFalse(leaked)


if __name__ == "__main__":
    unittest.main()
