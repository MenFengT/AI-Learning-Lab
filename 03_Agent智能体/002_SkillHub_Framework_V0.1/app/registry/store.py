"""Registry存储实现。"""

from .exceptions import DuplicateSkillError, SkillNotFoundError
from .models import SkillRegistration


class InMemoryRegistryStore:
    """进程内Descriptor存储，不保存业务Skill实例。"""

    def __init__(self) -> None:
        self._registrations: dict[str, SkillRegistration] = {}

    def add(self, registration: SkillRegistration) -> None:
        if registration.skill_id in self._registrations:
            raise DuplicateSkillError(f"Skill已注册：{registration.skill_id}")
        self._registrations[registration.skill_id] = registration

    def remove(self, skill_id: str) -> SkillRegistration:
        try:
            return self._registrations.pop(skill_id)
        except KeyError as exc:
            raise SkillNotFoundError(f"Skill不存在：{skill_id}") from exc

    def get(self, skill_id: str) -> SkillRegistration | None:
        return self._registrations.get(skill_id)

    def list_all(self) -> tuple[SkillRegistration, ...]:
        return tuple(self._registrations[key] for key in sorted(self._registrations))
