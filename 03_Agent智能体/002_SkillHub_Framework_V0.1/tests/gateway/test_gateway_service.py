import unittest

from app.gateway import (
    AgentArtifactReference,
    AgentInvocationResult,
    AgentResponse,
    AsyncTaskStatus,
    InteractionGateway,
    InteractionGatewayProtocol,
    UserMessage,
)


class RecordingAgentAdapter:
    def __init__(self) -> None:
        self.messages: list[UserMessage] = []

    def invoke(self, message: UserMessage) -> AgentInvocationResult:
        self.messages.append(message)
        return AgentInvocationResult(
            task_id="task-001",
            status=AsyncTaskStatus.COMPLETED,
            message="处理完成",
            artifacts=(
                AgentArtifactReference(
                    "artifact-001", 1, "DOCUMENT", "result.docx"
                ),
            ),
            metadata={"trace_id": "trace-001"},
        )


class GatewayServiceTests(unittest.TestCase):
    def test_gateway_only_invokes_agent_port_and_normalizes_response(self) -> None:
        adapter = RecordingAgentAdapter()
        gateway = InteractionGateway(adapter)
        message = UserMessage("message-001", "user-001", "生成报告")

        response = gateway.handle(message)

        self.assertIsInstance(gateway, InteractionGatewayProtocol)
        self.assertIsInstance(response, AgentResponse)
        self.assertEqual(adapter.messages, [message])
        self.assertEqual(response.task_id, "task-001")
        self.assertEqual(response.status, AsyncTaskStatus.COMPLETED)
        self.assertEqual(response.artifacts[0].artifact_id, "artifact-001")


if __name__ == "__main__":
    unittest.main()
