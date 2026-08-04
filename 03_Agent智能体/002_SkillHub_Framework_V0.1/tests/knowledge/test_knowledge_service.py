import tempfile
import unittest
from pathlib import Path

from app.services.audit import InMemoryAuditService
from app.services.governance import (
    AuditPolicy,
    CircuitCallPolicy,
    GovernanceConfig,
    Idempotency,
    OperationType,
    ServiceCallExecutor,
    ServiceCallPolicy,
)
from app.services.knowledge import (
    KnowledgeAccessPolicy,
    KnowledgeDocumentRequest,
    KnowledgeMetadataRequest,
    KnowledgePermission,
    KnowledgeQueryRequest,
    KnowledgeRuntimeContext,
    KnowledgeSearchRequest,
    KnowledgeService,
    KnowledgeServiceProtocol,
)
from app.services.models import MCPRequest, MCPResponse
from app.services.resilience import (
    CircuitBreaker,
    CircuitBreakerPolicy,
    CircuitKey,
    RetryExecutor,
    RetryPolicy,
)

from .test_knowledge_mcp import build_client
from .test_knowledge_router import build_roots


SKILL_ID = "local/material_plan@0.2.0"
TIMEOUT_ERROR = "SHF-MCP-CLIENT-TIMEOUT"


class FakeClock:
    def __init__(self) -> None:
        self.current = 0.0

    def now(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current += seconds


def governance_policy() -> ServiceCallPolicy:
    return ServiceCallPolicy(
        operation_type=OperationType.READ,
        idempotency=Idempotency.IDEMPOTENT,
        retry_policy=RetryPolicy(
            max_attempts=2,
            initial_delay_seconds=0,
            max_delay_seconds=0,
            backoff_multiplier=1,
            retryable_error_codes=frozenset({TIMEOUT_ERROR}),
        ),
        circuit_policy=CircuitCallPolicy(
            failure_error_codes=frozenset({TIMEOUT_ERROR})
        ),
        audit_policy=AuditPolicy(),
        timeout_budget=5.0,
    )


def build_governance(
    client: object,
    *,
    audit: InMemoryAuditService | None = None,
    breaker: CircuitBreaker | None = None,
    clock: FakeClock | None = None,
) -> tuple[ServiceCallExecutor, InMemoryAuditService, CircuitBreaker]:
    governance_clock = clock or FakeClock()
    audit_service = audit or InMemoryAuditService()
    circuit_breaker = breaker or CircuitBreaker(
        CircuitBreakerPolicy(
            failure_threshold=2,
            recovery_timeout_seconds=10.0,
        ),
        governance_clock,
    )
    return (
        ServiceCallExecutor(
            mcp_client=client,  # type: ignore[arg-type]
            audit_service=audit_service,
            retry_executor=RetryExecutor(governance_clock),
            circuit_breaker=circuit_breaker,
            clock=governance_clock,
            config=GovernanceConfig(),
        ),
        audit_service,
        circuit_breaker,
    )


def access_policy() -> KnowledgeAccessPolicy:
    return KnowledgeAccessPolicy(
        {
            SKILL_ID: frozenset(
                {
                    KnowledgePermission.KNOWLEDGE_READ,
                    KnowledgePermission.STANDARDS_READ,
                    KnowledgePermission.KNOWLEDGE_DOCUMENT_READ,
                }
            )
        }
    )


def runtime() -> KnowledgeRuntimeContext:
    return KnowledgeRuntimeContext(
        task_id="task-001",
        trace_id="trace-001",
        span_id="span-001",
        skill_id=SKILL_ID,
    )


class KnowledgeServiceTests(unittest.TestCase):
    def test_query_through_mcp_returns_sources_and_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            domain, standards = build_roots(Path(directory))
            client, _ = build_client(domain, standards)
            executor, audit, _ = build_governance(client)
            service = KnowledgeService(
                executor, access_policy(), governance_policy()
            )
            result = service.query(
                KnowledgeQueryRequest(runtime(), "混凝土", 5.0)
            )

        self.assertIsInstance(service, KnowledgeServiceProtocol)
        self.assertTrue(result.success)
        self.assertEqual(
            result.data.domain_results[0].source.document_id,
            "domain.concrete",
        )
        self.assertEqual(
            result.data.standards_results[0].source.document_id,
            "standard.concrete",
        )
        self.assertEqual(result.data.conflicts[0].rule_key, "concrete.grade")
        self.assertEqual(
            [event.metadata["event_type"] for event in audit.events()],
            ["SERVICE_CALL_STARTED", "SERVICE_CALL_SUCCEEDED"],
        )

    def test_document_permission_is_required(self) -> None:
        class UnexpectedExecutor:
            calls = 0

            def execute(self, request: object, context: object, policy: object) -> object:
                self.calls += 1
                raise AssertionError("权限拒绝时不得调用Governance")

        executor = UnexpectedExecutor()
        service = KnowledgeService(
            executor,  # type: ignore[arg-type]
            KnowledgeAccessPolicy(
                {SKILL_ID: frozenset({KnowledgePermission.KNOWLEDGE_READ})}
            ),
            governance_policy(),
        )
        result = service.get_document(
            KnowledgeDocumentRequest(runtime(), "domain.concrete", 5.0)
        )

        self.assertFalse(result.success)
        self.assertEqual(
            result.error_code, "SHF-SVC-KNOWLEDGE-PERMISSION_DENIED"
        )
        self.assertEqual(executor.calls, 0)

    def test_query_requires_standards_permission(self) -> None:
        class UnexpectedExecutor:
            calls = 0

            def execute(self, request: object, context: object, policy: object) -> object:
                self.calls += 1
                raise AssertionError("权限拒绝时不得调用Governance")

        executor = UnexpectedExecutor()
        service = KnowledgeService(
            executor,  # type: ignore[arg-type]
            KnowledgeAccessPolicy(
                {SKILL_ID: frozenset({KnowledgePermission.KNOWLEDGE_READ})}
            ),
            governance_policy(),
        )
        result = service.query(KnowledgeQueryRequest(runtime(), "混凝土", 5.0))

        self.assertFalse(result.success)
        self.assertEqual(executor.calls, 0)

        search_result = service.search(
            KnowledgeSearchRequest(runtime(), "混凝土", 5.0)
        )
        self.assertFalse(search_result.success)
        self.assertEqual(executor.calls, 0)

        document_result = service.get_document(
            KnowledgeDocumentRequest(
                runtime(), "standard.concrete", 5.0
            )
        )
        self.assertFalse(document_result.success)
        self.assertEqual(executor.calls, 0)

        metadata_result = service.get_metadata(
            KnowledgeMetadataRequest(
                runtime(), "standard.concrete", 5.0
            )
        )
        self.assertFalse(metadata_result.success)
        self.assertEqual(executor.calls, 0)

    def test_runtime_context_and_policy_reach_governance(self) -> None:
        class RecordingExecutor:
            def __init__(self) -> None:
                self.request: MCPRequest | None = None
                self.context = None
                self.policy = None

            def execute(self, request, context, policy) -> MCPResponse:
                self.request = request
                self.context = context
                self.policy = policy
                return MCPResponse(
                    success=True,
                    content={"results": []},
                    error_code=None,
                    message="ok",
                    server_name=request.server_name,
                    tool_name=request.tool_name,
                    trace_id=request.runtime_context.trace_id,
                    span_id=request.runtime_context.span_id,
                    duration_ms=1.0,
                    attempts=1,
                )

        executor = RecordingExecutor()
        service = KnowledgeService(
            executor,  # type: ignore[arg-type]
            access_policy(),
            governance_policy(),
        )

        result = service.search(
            KnowledgeSearchRequest(runtime(), "混凝土", 5.0)
        )

        self.assertTrue(result.success)
        assert executor.request is not None
        self.assertEqual(executor.request.runtime_context.task_id, "task-001")
        self.assertEqual(executor.request.runtime_context.trace_id, "trace-001")
        self.assertEqual(executor.request.runtime_context.skill_id, SKILL_ID)
        self.assertNotEqual(
            executor.request.runtime_context.span_id, "span-001"
        )
        self.assertEqual(executor.context.service_span_id, executor.request.runtime_context.span_id)
        self.assertEqual(executor.context.parent_span_id, "span-001")
        self.assertEqual(executor.context.service_name, "knowledge-service")
        self.assertEqual(executor.context.operation_name, "search")
        self.assertEqual(executor.policy.operation_type, OperationType.READ)
        self.assertEqual(executor.policy.idempotency, Idempotency.IDEMPOTENT)

    def test_retry_failure_and_audit_failed_event(self) -> None:
        class TimeoutClient:
            calls = 0

            def call(self, request: MCPRequest) -> MCPResponse:
                self.calls += 1
                return MCPResponse(
                    success=False,
                    content=None,
                    error_code=TIMEOUT_ERROR,
                    message="timeout",
                    server_name=request.server_name,
                    tool_name=request.tool_name,
                    trace_id=request.runtime_context.trace_id,
                    span_id=request.runtime_context.span_id,
                    duration_ms=1.0,
                    attempts=1,
                )

        client = TimeoutClient()
        executor, audit, _ = build_governance(client)
        service = KnowledgeService(
            executor, access_policy(), governance_policy()
        )

        result = service.query(
            KnowledgeQueryRequest(runtime(), "混凝土", 5.0)
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, TIMEOUT_ERROR)
        self.assertEqual(client.calls, 2)
        self.assertEqual(
            [event.metadata["event_type"] for event in audit.events()],
            ["SERVICE_CALL_STARTED", "SERVICE_CALL_FAILED"],
        )

    def test_open_circuit_rejects_mcp_call(self) -> None:
        class UnexpectedClient:
            calls = 0

            def call(self, request: MCPRequest) -> MCPResponse:
                self.calls += 1
                raise AssertionError("OPEN状态不得调用MCP")

        clock = FakeClock()
        breaker = CircuitBreaker(
            CircuitBreakerPolicy(
                failure_threshold=1,
                recovery_timeout_seconds=10.0,
            ),
            clock,
        )
        key = CircuitKey("knowledge-server", "knowledge.query")
        breaker.record_failure(key)
        client = UnexpectedClient()
        executor, audit, _ = build_governance(
            client, breaker=breaker, clock=clock
        )
        service = KnowledgeService(
            executor, access_policy(), governance_policy()
        )

        result = service.query(
            KnowledgeQueryRequest(runtime(), "混凝土", 5.0)
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "SHF-SVC-GOV-CIRCUIT_OPEN")
        self.assertEqual(client.calls, 0)
        self.assertEqual(
            [event.metadata["event_type"] for event in audit.events()],
            ["SERVICE_CALL_STARTED", "SERVICE_CALL_FAILED"],
        )


if __name__ == "__main__":
    unittest.main()
