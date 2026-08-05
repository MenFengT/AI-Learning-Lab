"""ContentPlanner、KnowledgeService和ContentGenerator的受控Service入口。"""

from typing import Any, Mapping
from uuid import uuid4

from app.content.errors import ContentError
from app.content.models import (
    ContentDraft,
    ContentGenerationContext,
    ContentPlanningRequest,
    KnowledgeFragment,
)
from app.content.protocols import ContentGeneratorProtocol, ContentPlannerProtocol
from app.runtime.invocation_context import InvocationContext
from app.runtime.trace import generate_span_id
from app.services.audit.models import AuditEvent
from app.services.audit.protocols import AuditServiceProtocol
from app.services.knowledge.models import (
    KnowledgeQueryRequest,
    KnowledgeRuntimeContext,
)
from app.services.knowledge.protocols import KnowledgeServiceProtocol
from app.services.models import ServiceResult
from app.services.resilience.clock import ClockProtocol

from .errors import (
    CONTENT_GENERATION_FAILED,
    CONTENT_KNOWLEDGE_FAILED,
    CONTENT_PLAN_FAILED,
)
from .models import ContentServiceRequest


class ContentService:
    """不接触MCP、文件、Office或Skill的内容编排边界。"""

    def __init__(
        self,
        planner: ContentPlannerProtocol,
        knowledge_service: KnowledgeServiceProtocol,
        generator: ContentGeneratorProtocol,
        audit_service: AuditServiceProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._planner = planner
        self._knowledge_service = knowledge_service
        self._generator = generator
        self._audit_service = audit_service
        self._clock = clock

    def generate_content(
        self, request: ContentServiceRequest
    ) -> ServiceResult[ContentDraft]:
        started_at = self._clock.now()
        service_span_id = generate_span_id()
        audit_errors: list[dict[str, str]] = []
        self._audit(
            "CONTENT_GENERATION_STARTED",
            request.runtime_context,
            service_span_id,
            started_at,
            None,
            audit_errors,
        )
        try:
            plan = self._planner.plan(
                ContentPlanningRequest(
                    document_type=request.document_type,
                    title=request.title,
                    requirements=request.requirements,
                    requested_sections=request.requested_sections,
                    metadata=_plain(request.metadata),
                )
            )
        except (ContentError, TypeError, ValueError):
            return self._failure(
                request,
                service_span_id,
                CONTENT_PLAN_FAILED,
                "内容结构规划失败",
                started_at,
                audit_errors,
            )

        knowledge_result = self._load_knowledge(
            request, plan.required_knowledge, service_span_id
        )
        if isinstance(knowledge_result, ServiceResult):
            return self._failure(
                request,
                service_span_id,
                CONTENT_KNOWLEDGE_FAILED,
                knowledge_result.message,
                started_at,
                audit_errors,
            )

        try:
            draft = self._generator.generate(
                plan,
                ContentGenerationContext(
                    title=request.title,
                    requirements=request.requirements,
                    knowledge=knowledge_result,
                    metadata={
                        **_plain(request.metadata),
                        "task_id": request.runtime_context.task_id,
                        "trace_id": request.runtime_context.trace_id,
                        "span_id": service_span_id,
                        "skill_id": request.runtime_context.skill_id,
                    },
                ),
            )
        except (ContentError, TypeError, ValueError):
            return self._failure(
                request,
                service_span_id,
                CONTENT_GENERATION_FAILED,
                "结构化内容生成失败",
                started_at,
                audit_errors,
            )

        self._audit(
            "CONTENT_GENERATION_SUCCEEDED",
            request.runtime_context,
            service_span_id,
            started_at,
            None,
            audit_errors,
        )
        return ServiceResult(
            success=True,
            data=draft,
            error_code=None,
            message="内容生成成功",
            trace_id=request.runtime_context.trace_id,
            metadata={
                "span_id": service_span_id,
                "audit_errors": tuple(audit_errors),
            },
        )

    def _load_knowledge(
        self,
        request: ContentServiceRequest,
        required_knowledge: tuple[str, ...],
        service_span_id: str,
    ) -> tuple[KnowledgeFragment, ...] | ServiceResult[Any]:
        if not required_knowledge and request.knowledge_query is None:
            return ()
        query_text = request.knowledge_query or (
            f"{request.requirements}；所需知识：{', '.join(required_knowledge)}"
        )
        context = request.runtime_context
        result = self._knowledge_service.query(
            KnowledgeQueryRequest(
                runtime_context=KnowledgeRuntimeContext(
                    task_id=context.task_id,
                    trace_id=context.trace_id,
                    span_id=service_span_id,
                    skill_id=context.skill_id,
                    user_id=context.user_id,
                    metadata=_plain(context.metadata),
                ),
                query_text=query_text,
                timeout=request.timeout,
            )
        )
        if not result.success or result.data is None:
            return result
        hits = (*result.data.domain_results, *result.data.standards_results)
        fallback_key = required_knowledge[0] if required_knowledge else "context"
        return tuple(
            KnowledgeFragment(
                knowledge_key=fallback_key,
                content=hit.content,
                source=hit.source.source,
                document_id=hit.source.document_id,
                version=hit.source.version,
            )
            for hit in hits
            if hit.content
        )

    def _failure(
        self,
        request: ContentServiceRequest,
        service_span_id: str,
        error_code: str,
        message: str,
        started_at: float,
        audit_errors: list[dict[str, str]],
    ) -> ServiceResult[ContentDraft]:
        self._audit(
            "CONTENT_GENERATION_FAILED",
            request.runtime_context,
            service_span_id,
            started_at,
            error_code,
            audit_errors,
        )
        return ServiceResult(
            success=False,
            data=None,
            error_code=error_code,
            message=message,
            trace_id=request.runtime_context.trace_id,
            metadata={
                "span_id": service_span_id,
                "audit_errors": tuple(audit_errors),
            },
        )

    def _audit(
        self,
        event_type: str,
        context: InvocationContext,
        service_span_id: str,
        started_at: float,
        error_code: str | None,
        errors: list[dict[str, str]],
    ) -> None:
        event = AuditEvent(
            task_id=context.task_id,
            trace_id=context.trace_id,
            span_id=service_span_id,
            skill_id=context.skill_id,
            server="content-service",
            tool="content.generate",
            duration=max(0.0, self._clock.now() - started_at),
            error_code=error_code,
            metadata={
                "event_id": uuid4().hex,
                "event_type": event_type,
                "parent_span_id": context.span_id,
            },
        )
        try:
            self._audit_service.record(event)
        except Exception as exc:
            errors.append(
                {
                    "event_type": event_type,
                    "error_type": type(exc).__name__,
                }
            )


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(child) for key, child in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(_plain(child) for child in value)
    return value
