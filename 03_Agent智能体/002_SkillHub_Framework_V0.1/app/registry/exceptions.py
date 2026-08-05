"""Skill Registry 的稳定异常类型。"""


class RegistryError(Exception):
    """Registry异常基类。"""


class DuplicateSkillError(RegistryError):
    """相同稳定身份的Skill已存在。"""


class SkillNotFoundError(RegistryError):
    """请求的Skill不存在。"""


class ActiveVersionConflictError(RegistryError):
    """同一命名空间和名称存在多个ACTIVE版本。"""


class ManifestValidationError(RegistryError, ValueError):
    """Skill Manifest不符合契约。"""
