"""DocumentSkill使用的外部端口；不包含任何基础设施实现。"""

from typing import Protocol

from app.services.content.protocols import ContentServiceProtocol
from app.services.office.protocols import OfficeServiceProtocol


class PromptLoaderProtocol(Protocol):
    def load(self, template_name: str) -> str: ...
