"""定义 Descriptor 与可执行 Skill 实例之间的装配边界。"""

from typing import Mapping, Protocol

from app.skills.base_skill import BaseSkill


class SkillResolver(Protocol):
    """按稳定 skill_id 获取由 Composition Root 创建的 Skill。"""

    def resolve(self, skill_id: str) -> BaseSkill: ...


class InMemorySkillResolver:
    """V0.2 本地装配实现；不承担注册、发现或生命周期管理。"""

    def __init__(self, bindings: Mapping[str, BaseSkill]) -> None:
        self._bindings = dict(bindings)

    def resolve(self, skill_id: str) -> BaseSkill:
        try:
            return self._bindings[skill_id]
        except KeyError as exc:
            raise LookupError(f"Skill未装配：{skill_id}") from exc
