from abc import ABC, abstractmethod

from app.core.context import TaskContext


class BaseSkill(ABC):
    """所有业务 Skill 必须实现的最小接口。"""

    name: str
    description: str
    keywords: tuple[str, ...] = ()
    is_default: bool = False

    @abstractmethod
    def execute(self, context: TaskContext) -> str:
        """执行本 Skill 的业务流程。Skill 不调用其他 Skill。"""
        raise NotImplementedError
