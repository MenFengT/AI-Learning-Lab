"""Construction Document Skill 稳定异常。"""


class ConstructionSkillError(Exception):
    """施工文档Skill异常基类。"""


class ConstructionRequestError(ConstructionSkillError):
    """施工文档请求无效。"""


class ConstructionTemplateError(ConstructionSkillError):
    """施工文档模板缺失或格式无效。"""


class ConstructionDependencyError(ConstructionSkillError):
    """Content或Knowledge依赖调用失败。"""
