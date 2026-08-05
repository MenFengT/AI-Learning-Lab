from app.adapters.agent import AgentTaskResult
from app.composition import ApplicationDependencies
from app.gateway.models import AsyncTaskStatus


class EmptyPlanDraftProvider:
    def generate_steps(self, request):
        return ()


class FakeAgentRuntimeInvocation:
    def __init__(self) -> None:
        self.calls = []

    def invoke(self, task):
        self.calls.append(task)
        return AgentTaskResult(
            task_id="task-gateway-001",
            status=AsyncTaskStatus.COMPLETED,
            message="完成",
        )


class RejectingAttachmentResolver:
    def resolve(self, attachment):
        raise AssertionError("本测试不包含附件")


class RecordingInvocationFactory:
    def __init__(self) -> None:
        self.calls = []
        self.invocation = FakeAgentRuntimeInvocation()

    def __call__(self, agent, runtime, planner, executor):
        self.calls.append((agent, runtime, planner, executor))
        return self.invocation


def dependencies(factory=None) -> ApplicationDependencies:
    return ApplicationDependencies(
        skill_registrations=(),
        skill_bindings={},
        plan_draft_provider=EmptyPlanDraftProvider(),
        agent_invocation_factory=factory or RecordingInvocationFactory(),
        telegram_attachment_resolver=RejectingAttachmentResolver(),
    )
