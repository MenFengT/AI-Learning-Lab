from app.content import (
    ContentDraft,
    ContentParagraph,
    ContentPlan,
    ContentSection,
)
from app.runtime.invocation_context import InvocationContext
from app.services.knowledge.models import (
    KnowledgeHit,
    KnowledgeQueryData,
    SourceReference,
)
from app.services.models import ServiceResult


def runtime_context() -> InvocationContext:
    return InvocationContext(
        task_id="task-content-001",
        trace_id="trace-content-001",
        span_id="span-skill-001",
        skill_id="local/document_automation@0.4.0",
    )


class Planner:
    def __init__(self) -> None:
        self.requests: list[object] = []

    def plan(self, request):
        self.requests.append(request)
        section = ContentSection(
            "summary", "概述", 1, "生成概述", ("domain_context",)
        )
        return ContentPlan(
            request.document_type,
            (section,),
            ("summary",),
            ("domain_context",),
        )


class Knowledge:
    def __init__(self, *, success: bool = True) -> None:
        self.success = success
        self.requests: list[object] = []

    def query(self, request):
        self.requests.append(request)
        if not self.success:
            return ServiceResult(
                False,
                None,
                "SHF-SVC-KNOWLEDGE-PERMISSION_DENIED",
                "knowledge denied",
                request.runtime_context.trace_id,
            )
        hit = KnowledgeHit(
            title="领域资料",
            content="可追溯领域内容",
            source=SourceReference(
                "domain.content",
                "1.0",
                "2026-01-01T00:00:00+00:00",
                "domain",
                "fragment-1",
                "DOMAIN",
            ),
            status="ACTIVE",
        )
        return ServiceResult(
            True,
            KnowledgeQueryData((hit,), (), ()),
            None,
            "ok",
            request.runtime_context.trace_id,
        )


class Generator:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object]] = []

    def generate(self, plan, context):
        self.calls.append((plan, context))
        return ContentDraft(
            context.title,
            plan.section_order,
            (ContentParagraph("summary", 1, "生成后的概述"),),
        )


class Clock:
    def __init__(self) -> None:
        self.value = 1.0

    def now(self):
        self.value += 0.1
        return self.value

    def sleep(self, seconds):
        self.value += seconds
