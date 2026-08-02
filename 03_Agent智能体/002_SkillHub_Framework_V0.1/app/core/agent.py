import re

from app.core.context import TaskContext
from app.core.skill_router import SkillRouter


class SkillHubAgent:
    """唯一 Agent：理解任务、拆解任务并调度 Skill。"""

    def __init__(self, skill_router: SkillRouter) -> None:
        self._skill_router = skill_router

    def run(self, user_task: str) -> str:
        task = user_task.strip()
        if not task:
            raise ValueError("用户任务不能为空")

        context = TaskContext(user_task=task, subtasks=self._decompose(task))
        skill = self._skill_router.select(task)
        return skill.execute(context)

    @staticmethod
    def _decompose(task: str) -> list[str]:
        """V0.1 使用确定性规则拆分任务，未来可替换任务理解组件。"""
        return [part.strip() for part in re.split(r"[，,；;。\n]+", task) if part.strip()]
