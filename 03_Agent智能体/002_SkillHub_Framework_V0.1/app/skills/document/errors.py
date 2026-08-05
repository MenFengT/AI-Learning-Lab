"""Document Automation Skill错误。"""


class DocumentSkillError(RuntimeError):
    """文档自动化业务错误。"""


class DocumentRequestError(DocumentSkillError):
    """文档任务输入不符合契约。"""


class DocumentDependencyError(DocumentSkillError):
    """依赖的Service调用失败。"""


class PromptLoadError(DocumentSkillError):
    """Prompt模板不存在或不安全。"""
