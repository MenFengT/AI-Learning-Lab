import unittest

from app.ingestion import FileIngestionRequest, FileIngestionService

from .helpers import RecordingFileSystem, attachment, file_reference, runtime


class FileReferenceResultTests(unittest.TestCase):
    def test_result_preserves_canonical_file_reference_identity(self) -> None:
        reference = file_reference()
        service = FileIngestionService(RecordingFileSystem((reference,)))

        result = service.ingest(
            FileIngestionRequest(
                "task-ingestion-001", attachment(), runtime()
            )
        )

        self.assertEqual(result.file_reference, reference)
        self.assertEqual(result.file_reference.file_id, "file-ingestion-001")
        self.assertEqual(result.file_reference.version, "1")
        self.assertEqual(result.checksum, reference.checksum)
        self.assertEqual(result.size, reference.metadata.size)


if __name__ == "__main__":
    unittest.main()
