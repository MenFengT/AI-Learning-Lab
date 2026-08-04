"""轻量Skill Registry服务。"""

from .exceptions import (
    ActiveVersionConflictError,
    DuplicateSkillError,
    SkillNotFoundError,
)
from .models import (
    HealthStatus,
    SkillLifecycleStatus,
    SkillRegistration,
    build_skill_id,
)
from .protocols import RegistryStore
from .store import InMemoryRegistryStore


class SkillRegistry:
    """管理Skill Descriptor、元数据、生命周期和健康状态。"""

    def __init__(self, store: RegistryStore | None = None) -> None:
        self._store = store or InMemoryRegistryStore()

    def register(self, registration: SkillRegistration) -> None:
        if self._store.get(registration.skill_id) is not None:
            raise DuplicateSkillError(f"Skill已注册：{registration.skill_id}")
        if registration.lifecycle_status is SkillLifecycleStatus.ACTIVE:
            active = [
                item
                for item in self.list_by_name(
                    registration.name, namespace=registration.namespace
                )
                if item.lifecycle_status is SkillLifecycleStatus.ACTIVE
            ]
            if active:
                raise ActiveVersionConflictError(
                    "同一namespace+name只能有一个ACTIVE版本："
                    f"{active[0].skill_id}"
                )
        self._store.add(registration)

    def unregister(self, skill_id: str) -> SkillRegistration:
        return self._store.remove(skill_id)

    def get(
        self, name: str, version: str, *, namespace: str = "local"
    ) -> SkillRegistration:
        skill_id = build_skill_id(namespace, name, version)
        registration = self._store.get(skill_id)
        if registration is None:
            raise SkillNotFoundError(f"Skill不存在：{skill_id}")
        return registration

    def list_all(self) -> tuple[SkillRegistration, ...]:
        return self._store.list_all()

    def list_by_name(
        self, name: str, *, namespace: str = "local"
    ) -> tuple[SkillRegistration, ...]:
        return tuple(
            item
            for item in self.list_all()
            if item.namespace == namespace and item.name == name
        )

    def find_candidates(self, task: str) -> tuple[SkillRegistration, ...]:
        normalized_task = task.strip().casefold()
        if not normalized_task:
            return ()
        candidates = [
            item
            for item in self.list_all()
            if item.lifecycle_status is SkillLifecycleStatus.ACTIVE
            and item.health_status
            in {HealthStatus.UNKNOWN, HealthStatus.HEALTHY, HealthStatus.DEGRADED}
            and any(
                keyword.casefold() in normalized_task
                for keyword in item.metadata.keywords
            )
        ]
        return tuple(
            sorted(
                candidates,
                key=lambda item: (
                    -max(
                        len(keyword)
                        for keyword in item.metadata.keywords
                        if keyword.casefold() in normalized_task
                    ),
                    item.skill_id,
                ),
            )
        )
