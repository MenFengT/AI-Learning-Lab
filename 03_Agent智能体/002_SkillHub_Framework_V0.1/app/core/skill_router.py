from app.registry.models import (
    HealthStatus,
    SkillLifecycleStatus,
    SkillRegistration,
)
from app.registry.protocols import SkillCatalog


class SkillRouter:
    """只向 SkillCatalog 请求候选并选择 Skill Descriptor。"""

    def __init__(self, catalog: SkillCatalog) -> None:
        self._catalog = catalog

    def select(self, task: str) -> SkillRegistration:
        candidates = self._catalog.find_candidates(task)
        if candidates:
            return candidates[0]
        raise LookupError(f"没有匹配任务的 Skill：{task}")

    def select_by_id(self, skill_id: str) -> SkillRegistration:
        """精确选择可执行版本，不承担实例解析或生命周期管理。"""
        registration = self._catalog.get_by_id(skill_id)
        if registration.lifecycle_status is not SkillLifecycleStatus.ACTIVE:
            raise LookupError(f"Skill不可执行：{skill_id}")
        if registration.health_status not in {
            HealthStatus.UNKNOWN,
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
        }:
            raise LookupError(f"Skill健康状态不可用：{skill_id}")
        return registration
