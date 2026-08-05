"""Knowledge Service最小权限策略。"""

from enum import Enum
from types import MappingProxyType
from typing import Mapping


class KnowledgePermission(str, Enum):
    KNOWLEDGE_READ = "KNOWLEDGE_READ"
    STANDARDS_READ = "STANDARDS_READ"
    KNOWLEDGE_DOCUMENT_READ = "KNOWLEDGE_DOCUMENT_READ"


class KnowledgeAccessPolicy:
    """按稳定skill_id提供只读权限快照。"""

    def __init__(
        self,
        grants: Mapping[str, frozenset[KnowledgePermission]],
    ) -> None:
        self._grants = MappingProxyType(dict(grants))

    def allows(self, skill_id: str, permission: KnowledgePermission) -> bool:
        return permission in self._grants.get(skill_id, frozenset())
