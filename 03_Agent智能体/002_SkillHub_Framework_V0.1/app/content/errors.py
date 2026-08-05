"""Content Generation Layer错误。"""


class ContentError(RuntimeError):
    """Content Layer基础错误。"""


class ContentTemplateError(ContentError):
    """内容模板不存在或不符合契约。"""


class ContentPlanningError(ContentError):
    """内容结构规划失败。"""


class ContentGenerationError(ContentError):
    """内容草稿生成失败。"""
