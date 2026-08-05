import unittest

from app.ingestion import (
    FileIngestionRequest,
    FileIngestionService,
    FileIngestionServiceProtocol,
    IngestionSource,
)

from .helpers import RecordingFileSystem, attachment, runtime


class AttachmentConversionTests(unittest.TestCase):
    def test_attachment_is_resolved_through_controlled_input_directory(self) -> None:
        filesystem = RecordingFileSystem()
        service = FileIngestionService(filesystem)
        request = FileIngestionRequest(
            "task-ingestion-001",
            attachment(),
            runtime(),
            IngestionSource.WEB,
        )

        result = service.ingest(request)

        self.assertIsInstance(service, FileIngestionServiceProtocol)
        self.assertEqual(result.metadata["source"], "WEB")
        fs_request = filesystem.requests[0]
        self.assertEqual(fs_request.source, "input/upload-001")
        self.assertEqual(fs_request.runtime_context.task_id, request.task_id)
        self.assertEqual(
            fs_request.runtime_context.trace_id,
            request.runtime_context.trace_id,
        )
        self.assertEqual(
            fs_request.runtime_context.span_id,
            request.runtime_context.span_id,
        )
        self.assertEqual(
            fs_request.runtime_context.skill_id,
            request.runtime_context.skill_id,
        )

    def test_all_future_sources_are_reserved(self) -> None:
        self.assertEqual(
            set(IngestionSource),
            {
                IngestionSource.TELEGRAM,
                IngestionSource.WEB,
                IngestionSource.WECHAT_WORK,
                IngestionSource.LOCAL_UPLOAD,
            },
        )


if __name__ == "__main__":
    unittest.main()
