"""DocumentSkill唯一允许依赖的Content Service协议。"""

from typing import Protocol, runtime_checkable

from app.content.models import ContentDraft
from app.services.models import ServiceResult

from .models import ContentServiceRequest


@runtime_checkable
class ContentServiceProtocol(Protocol):
    def generate_content(
        self, request: ContentServiceRequest
    ) -> ServiceResult[ContentDraft]: ...
