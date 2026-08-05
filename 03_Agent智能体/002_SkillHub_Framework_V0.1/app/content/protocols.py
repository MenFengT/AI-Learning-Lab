"""Content Layer规划、生成与模板端口。"""

from typing import Protocol, runtime_checkable

from .models import (
    ContentDraft,
    ContentGenerationContext,
    ContentPlan,
    ContentPlanningRequest,
    ContentSection,
    ContentTemplate,
)


@runtime_checkable
class ContentTemplateLoaderProtocol(Protocol):
    def load(self, document_type: str) -> ContentTemplate: ...


@runtime_checkable
class ContentPlannerProtocol(Protocol):
    def plan(self, request: ContentPlanningRequest) -> ContentPlan: ...


@runtime_checkable
class TextGenerationProviderProtocol(Protocol):
    """未来可由受控LLM实现；不拥有循环、Skill或Tool调用权。"""

    def generate(
        self,
        section: ContentSection,
        context: ContentGenerationContext,
    ) -> tuple[str, ...]: ...


@runtime_checkable
class ContentGeneratorProtocol(Protocol):
    def generate(
        self,
        plan: ContentPlan,
        context: ContentGenerationContext,
    ) -> ContentDraft: ...
