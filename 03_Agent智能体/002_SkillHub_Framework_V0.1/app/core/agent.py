import re

from app.core.context import TaskContext
from app.core.skill_resolver import SkillResolver
from app.core.skill_router import SkillRouter
from app.runtime.lifecycle import LifecycleStatus
from app.runtime.runtime_manager import RuntimeManager


class SkillHubAgent:
    """唯一 Agent：理解任务、拆解任务并调度 Skill。"""

    def __init__(
        self,
        skill_router: SkillRouter,
        runtime_manager: RuntimeManager,
        skill_resolver: SkillResolver,
    ) -> None:
        self._skill_router = skill_router
        self._runtime_manager = runtime_manager
        self._skill_resolver = skill_resolver

    def run(self, user_task: str, *, user_id: str | None = None) -> str:
        task = user_task.strip()
        if not task:
            raise ValueError("用户任务不能为空")

        environment = self._runtime_manager.create_environment(
            task, user_id=user_id
        )
        task_id = environment.context.task_id
        try:
            self._runtime_manager.transition(task_id, LifecycleStatus.PLANNING)
            registration = self._skill_router.select(task)
            invocation = self._runtime_manager.create_invocation_context(
                task_id, registration.skill_id
            )
            skill = self._skill_resolver.resolve(registration.skill_id)
            context = TaskContext(
                user_task=task,
                subtasks=self._decompose(task),
                invocation_context=invocation,
            )
            self._runtime_manager.transition(task_id, LifecycleStatus.EXECUTING)
            result = skill.execute(context)
            self._runtime_manager.complete(task_id, {"result": result})
            return result
        except Exception as exc:
            try:
                self._runtime_manager.fail(task_id, str(exc))
            except Exception as failure_exc:
                environment.context.metadata["failure_transition_error"] = {
                    "error_type": type(failure_exc).__name__,
                    "error": str(failure_exc),
                }
            raise

    @staticmethod
    def _decompose(task: str) -> list[str]:
        """V0.1 使用确定性规则拆分任务，未来可替换任务理解组件。"""
        return [part.strip() for part in re.split(r"[，,；;。\n]+", task) if part.strip()]
