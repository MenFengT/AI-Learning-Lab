"""Document Automation Skill公共接口。"""

from .errors import DocumentDependencyError, DocumentRequestError, DocumentSkillError
from .models import DocumentRequest, DocumentType
from .prompt_loader import PackagePromptLoader
from .protocols import (
    ContentServiceProtocol,
    OfficeServiceProtocol,
    PromptLoaderProtocol,
)
from .skill import DocumentSkill

__all__ = [
    "DocumentDependencyError",
    "DocumentRequest",
    "DocumentRequestError",
    "DocumentSkill",
    "DocumentSkillError",
    "DocumentType",
    "ContentServiceProtocol",
    "OfficeServiceProtocol",
    "PackagePromptLoader",
    "PromptLoaderProtocol",
]
