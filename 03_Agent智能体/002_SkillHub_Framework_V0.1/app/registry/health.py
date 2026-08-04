"""Skill Descriptor、Manifest和Skill类契约的无副作用健康检查。"""

from inspect import isabstract
from typing import Any

from app.skills.base_skill import BaseSkill

from .models import HealthCheckResult, HealthStatus, SkillRegistration


def check_registration_health(
    registration: SkillRegistration,
    skill_type: type[BaseSkill] | None = None,
) -> HealthCheckResult:
    """检查静态契约；绝不实例化Skill或调用execute。"""
    errors: list[str] = []
    if not registration.metadata.inputs:
        errors.append("metadata.inputs为空")
    if not registration.metadata.outputs:
        errors.append("metadata.outputs为空")
    if not registration.metadata.keywords:
        errors.append("metadata.keywords为空")

    if skill_type is not None:
        if not isinstance(skill_type, type) or not issubclass(skill_type, BaseSkill):
            errors.append("Skill必须继承BaseSkill")
        elif isabstract(skill_type):
            errors.append("Skill不能是抽象类")
        else:
            if getattr(skill_type, "name", None) != registration.name:
                errors.append("Skill.name与Manifest不一致")
            execute_method: Any = getattr(skill_type, "execute", None)
            if not callable(execute_method):
                errors.append("Skill缺少execute契约")

    if errors:
        return HealthCheckResult(HealthStatus.UNHEALTHY, tuple(errors))
    return HealthCheckResult(HealthStatus.HEALTHY)
