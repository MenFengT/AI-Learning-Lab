import tempfile
import unittest
from pathlib import Path

from app.services.filesystem import (
    FileOperationRequest,
    FilePermission,
    FileSystemRuntimeContext,
    FileSystemServiceProtocol,
)
from app.services.resilience import (
    CircuitBreaker,
    CircuitBreakerPolicy,
    CircuitKey,
    SystemClock,
)

from .helpers import SKILL_ID, build_service


def runtime() -> FileSystemRuntimeContext:
    return FileSystemRuntimeContext("task-001", "trace-001", "span-001", SKILL_ID)


class FileSystemServiceTests(unittest.TestCase):
    def test_write_read_and_runtime_context_through_mcp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, audit, transport = build_service(Path(directory))
            written = service.write_file(
                FileOperationRequest(runtime(), target="processing/test.txt", content=b"hello")
            )
            read = service.read_file(
                FileOperationRequest(runtime(), source="processing/test.txt")
            )

        self.assertIsInstance(service, FileSystemServiceProtocol)
        self.assertTrue(written.success)
        self.assertEqual(written.data.file.version, "1")
        self.assertEqual(read.data.content, b"hello")
        self.assertEqual(read.data.file.file_id, written.data.file.file_id)
        context = transport.last_payload["params"]["_meta"]
        self.assertEqual(context["task_id"], "task-001")
        self.assertEqual(context["trace_id"], "trace-001")
        self.assertEqual(context["skill_id"], SKILL_ID)
        self.assertNotEqual(context["span_id"], "span-001")
        self.assertTrue(transport.closed)
        self.assertEqual(len(audit.events()), 4)
        self.assertEqual(
            [event.metadata["event_type"] for event in audit.events()],
            [
                "SERVICE_CALL_STARTED",
                "SERVICE_CALL_SUCCEEDED",
                "SERVICE_CALL_STARTED",
                "SERVICE_CALL_SUCCEEDED",
            ],
        )
        self.assertEqual(audit.events()[0].metadata["operation_name"], "write")

    def test_content_change_increments_version_move_preserves_it_and_copy_gets_new_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, _, _ = build_service(Path(directory))
            first = service.write_file(FileOperationRequest(runtime(), target="processing/a.txt", content=b"one"))
            second = service.write_file(FileOperationRequest(runtime(), target="processing/a.txt", content=b"two", overwrite=True, expected_version="1"))
            moved = service.move_file(FileOperationRequest(runtime(), source="processing/a.txt", target="output/a.txt"))
            copied = service.copy_file(FileOperationRequest(runtime(), source="output/a.txt", target="processing/copy.txt"))

        self.assertEqual(first.data.file.version, "1")
        self.assertEqual(second.data.file.version, "2")
        self.assertEqual(moved.data.file.version, "2")
        self.assertEqual(moved.data.file.file_id, second.data.file.file_id)
        self.assertEqual(copied.data.file.version, "1")
        self.assertNotEqual(copied.data.file.file_id, moved.data.file.file_id)
        self.assertEqual(copied.data.file.source_file_id, moved.data.file.file_id)

    def test_size_limit_and_permission_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service, audit, transport = build_service(Path(directory), max_size=3)
            too_large = service.write_file(FileOperationRequest(runtime(), target="processing/large.bin", content=b"1234"))
            denied_service, denied_audit, denied_transport = build_service(Path(directory), permissions=frozenset({FilePermission.READ}))
            denied = denied_service.write_file(FileOperationRequest(runtime(), target="processing/no.txt", content=b"x"))

        self.assertFalse(too_large.success)
        self.assertEqual(too_large.error_code, "SHF-SVC-FILE-TOO_LARGE")
        self.assertFalse(denied.success)
        self.assertEqual(denied.error_code, "SHF-SVC-FILE-PERMISSION_DENIED")
        self.assertIsNone(denied_transport.last_payload)
        self.assertEqual(denied_audit.events()[0].metadata["result"], "FAILED")

    def test_open_circuit_rejects_read_without_mcp_call(self) -> None:
        clock = SystemClock()
        breaker = CircuitBreaker(
            CircuitBreakerPolicy(
                failure_threshold=1,
                recovery_timeout_seconds=10.0,
            ),
            clock,
        )
        breaker.record_failure(
            CircuitKey("filesystem-server", "filesystem.read")
        )
        with tempfile.TemporaryDirectory() as directory:
            service, audit, transport = build_service(
                Path(directory),
                clock=clock,
                circuit_breaker=breaker,
            )
            service.write_file(
                FileOperationRequest(
                    runtime(),
                    target="processing/test.txt",
                    content=b"hello",
                )
            )
            calls_before_read = transport.send_calls

            result = service.read_file(
                FileOperationRequest(
                    runtime(), source="processing/test.txt"
                )
            )

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "SHF-SVC-GOV-CIRCUIT_OPEN")
        self.assertEqual(transport.send_calls, calls_before_read)
        self.assertEqual(
            [event.metadata["event_type"] for event in audit.events()][-2:],
            ["SERVICE_CALL_STARTED", "SERVICE_CALL_FAILED"],
        )


if __name__ == "__main__":
    unittest.main()
