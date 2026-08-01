from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """所有 Skill 的统一接口。"""

    name = None

    @abstractmethod
    def run(self, *args, **kwargs):
        """执行单一能力并返回结果。"""
        raise NotImplementedError
