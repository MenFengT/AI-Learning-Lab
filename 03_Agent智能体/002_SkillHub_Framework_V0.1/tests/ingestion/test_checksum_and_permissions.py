import unittest

from app.ingestion import FileIngestionError, FileIngestionRequest, FileIngestionService

from .helpers import RecordingFileSystem, attachment, runtime


class ChecksumAndPermissionTests(unittest.TestCase):
    def test_checksum_or_size_mismatch_is_rejected(self) -> None:
        service = FileIngestionService(RecordingFileSystem())
        for invalid in (
            attachment(checksum="fedcba9876543210"),
            attachment(size=127),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(FileIngestionError) as captured:
                    service.ingest(
                        FileIngestionRequest(
                            "task-ingestion-001", invalid, runtime()
                        )
                    )
                self.assertEqual(
                    captured.exception.error_code,
                    "SHF-INGESTION-FILE-CHECKSUM_MISMATCH",
                )

    def test_filesystem_permission_denial_is_not_bypassed(self) -> None:
        filesystem = RecordingFileSystem(allowed=False)
        service = FileIngestionService(filesystem)
        with self.assertRaises(FileIngestionError) as captured:
            service.ingest(
                FileIngestionRequest(
                    "task-ingestion-001", attachment(), runtime()
                )
            )
        self.assertEqual(
            captured.exception.error_code,
            "SHF-INGESTION-FILESYSTEM-FAILED",
        )
        self.assertEqual(len(filesystem.requests), 1)


if __name__ == "__main__":
    unittest.main()
