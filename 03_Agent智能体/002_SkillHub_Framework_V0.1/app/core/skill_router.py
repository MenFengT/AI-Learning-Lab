from app.registry.models import SkillRegistration
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
