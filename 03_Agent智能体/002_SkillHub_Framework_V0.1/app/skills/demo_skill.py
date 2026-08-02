from app.core.context import TaskContext

from .base_skill import BaseSkill


class DemoSkill(BaseSkill):
    """最小演示 Skill：确认任务已经通过 Framework 完成调度。"""

    name = "demo"
    description = "处理演示、测试和通用任务"
    keywords = ("演示", "测试", "demo", "任务")
    is_default = True

    def execute(self, context: TaskContext) -> str:
        subtasks = "；".join(context.subtasks) or context.user_task
        return f"DemoSkill 已处理任务：{subtasks}"
