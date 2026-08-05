"""按ContentPlan生成结构化草稿，不访问任何基础设施。"""

from .errors import ContentGenerationError
from .models import (
    ContentDraft,
    ContentGenerationContext,
    ContentParagraph,
    ContentPlan,
)
from .protocols import TextGenerationProviderProtocol


class ContentGenerator:
    """确定性遍历计划章节，执行权仅限正文生成端口。"""

    def __init__(self, provider: TextGenerationProviderProtocol) -> None:
        self._provider = provider

    def generate(
        self,
        plan: ContentPlan,
        context: ContentGenerationContext,
    ) -> ContentDraft:
        paragraphs: list[ContentParagraph] = []
        paragraph_order = 1
        for section in plan.sections:
            try:
                generated = tuple(self._provider.generate(section, context))
            except Exception as exc:
                raise ContentGenerationError(
                    f"章节内容生成失败：{section.section_id}"
                ) from exc
            if not generated or any(
                not isinstance(text, str) or not text.strip()
                for text in generated
            ):
                raise ContentGenerationError(
                    f"章节生成结果无效：{section.section_id}"
                )
            for text in generated:
                paragraphs.append(
                    ContentParagraph(
                        section_id=section.section_id,
                        order=paragraph_order,
                        text=text.strip(),
                    )
                )
                paragraph_order += 1
        return ContentDraft(
            title=context.title,
            sections=plan.section_order,
            paragraphs=tuple(paragraphs),
            metadata={
                "document_type": plan.document_type,
                "required_knowledge": plan.required_knowledge,
            },
        )
