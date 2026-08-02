from abc import ABC, abstractmethod
from typing import Any


class ToolBase(ABC):
    """外部能力工具的统一抽象。"""

    name: str

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """执行文件、API 或外部系统操作。"""
        raise NotImplementedError
