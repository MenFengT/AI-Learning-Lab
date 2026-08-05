from app.composition import bootstrap
from app.gateway.models import AsyncTaskStatus, UserMessage

from .helpers import RecordingInvocationFactory, dependencies


def test_gateway_to_agent_invocation_chain_is_created() -> None:
    factory = RecordingInvocationFactory()
    container = bootstrap(dependencies(factory))

    response = container.gateway.handle(
        UserMessage(
            message_id="message-001",
            user_id="user-001",
            text="生成报告",
        )
    )

    assert response.task_id == "task-gateway-001"
    assert response.status is AsyncTaskStatus.COMPLETED
    assert len(factory.invocation.calls) == 1
    assert factory.invocation.calls[0].user_task == "生成报告"
