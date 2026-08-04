"""MCP Server端权限策略，防止调用方绕过Service边界。"""

from types import MappingProxyType
from typing import Mapping, Protocol


class MCPServerPermissionPolicyProtocol(Protocol):
    """按稳定Skill身份校验固定Tool权限。"""

    def allows(self, skill_id: str, permission: str) -> bool: ...


class InMemoryMCPServerPermissionPolicy:
    """由Composition Root注入的不可变进程内权限快照。"""

    def __init__(self, grants: Mapping[str, frozenset[str]]) -> None:
        self._grants = MappingProxyType(
            {
                skill_id: frozenset(permissions)
                for skill_id, permissions in grants.items()
            }
        )

    def allows(self, skill_id: str, permission: str) -> bool:
        return permission in self._grants.get(skill_id, frozenset())


class DenyAllMCPServerPermissionPolicy:
    """安全默认策略：未装配权限时拒绝全部Tool调用。"""

    def allows(self, skill_id: str, permission: str) -> bool:
        return False
