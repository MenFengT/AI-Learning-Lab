import unittest

from app.gateway import (
    AgentArtifactReference,
    AgentResponse,
    AsyncTaskStatus,
)


class ResponseModelTests(unittest.TestCase):
    def test_all_async_states_have_stable_response_contract(self) -> None:
        artifact = AgentArtifactReference(
            "artifact-001", 1, "DOCUMENT", "result.docx"
        )
        for status in AsyncTaskStatus:
            with self.subTest(status=status):
                response = AgentResponse(
                    task_id="task-001",
                    status=status,
                    message=f"status={status.value}",
                    artifacts=(artifact,) if status is AsyncTaskStatus.COMPLETED else (),
                    metadata={"progress": {"current": 1}},
                )
                self.assertEqual(response.status, status)
                self.assertEqual(response.schema_version, "0.1")


if __name__ == "__main__":
    unittest.main()
