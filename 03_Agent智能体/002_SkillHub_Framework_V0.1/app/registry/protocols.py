"""Registry的只读目录与存储协议。"""

from typing import Protocol

from .models import SkillRegistration


class RegistryStore(Protocol):
    def add(self, registration: SkillRegistration) -> None: ...

    def remove(self, skill_id: str) -> SkillRegistration: ...

    def get(self, skill_id: str) -> SkillRegistration | None: ...

    def list_all(self) -> tuple[SkillRegistration, ...]: ...


class SkillCatalog(Protocol):
    def get(
        self, name: str, version: str, *, namespace: str = "local"
    ) -> SkillRegistration: ...

    def list_by_name(
        self, name: str, *, namespace: str = "local"
    ) -> tuple[SkillRegistration, ...]: ...

    def find_candidates(self, task: str) -> tuple[SkillRegistration, ...]: ...
