from app.adapters.agent import AgentAdapter

from .helpers import FakeAgentRuntime, make_message


def test_gateway_request_is_converted_to_agent_task() -> None:
    runtime = FakeAgentRuntime()

    AgentAdapter(runtime).invoke(make_message())

    task = runtime.calls[0]
    assert task.message_id == "message-001"
    assert task.user_id == "user-001"
    assert task.user_task == "生成项目报告"
    assert task.metadata["channel"] == "telegram"
    assert len(task.attachments) == 1
    attachment = task.attachments[0]
    assert attachment.reference_id == "file-001"
    assert attachment.file_name == "source.docx"
    assert attachment.checksum == "a" * 64
