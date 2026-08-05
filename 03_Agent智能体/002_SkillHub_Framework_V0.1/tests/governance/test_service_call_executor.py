import unittest
from dataclasses import replace

from app.runtime.invocation_context import InvocationContext
from app.services.audit import AuditEvent, InMemoryAuditService
from app.services.governance import (
    AuditFailureMode,
    AuditPolicy,
    CircuitCallPolicy,
    GovernanceConfig,
    Idempotency,
    OperationType,
    ServiceCallContext,
    ServiceCallExecutor,
    ServiceCallExecutorProtocol,
    ServiceCallPolicy,
)
from app.services.governance.errors import (
    CIRCUIT_OPEN,
    CONTEXT_INVALID,
    EXECUTION_FAILED,
)
from app.services.models import MCPRequest, MCPResponse
from app.services.resilience import CircuitKey, CircuitOpenError, RetryPolicy


class FakeClock:
    def __init__(self) -> None:
        self.current = 0.0

    def now(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current += seconds


class RecordingMCPClient:
    def __init__(self, events: list[str], response: MCPResponse) -> None:
        self.events = events
        self.response = response
        self.calls = 0

    def call(self, request: MCPRequest) -> MCPResponse:
        self.events.append("mcp")
        self.calls += 1
        return self.response


class RaisingMCPClient(RecordingMCPClient):
    def call(self, request: MCPRequest) -> MCPResponse:
        self.events.append("mcp")
        self.calls += 1
        raise RuntimeError("transport failed")


class RecordingRetryExecutor:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.calls = 0

    def execute(self, operation, policy, *, timeout_seconds):
        self.events.append("retry")
        self.calls += 1
        return operation()


class RecordingCircuitBreaker:
    def __init__(self, events: list[str], *, opened: bool = False) -> None:
        self.events = events
        self.opened = opened
        self.successes = 0
        self.failures = 0

    def allow_request(self, key: CircuitKey) -> None:
        self.events.append("circuit")
        if self.opened:
            raise CircuitOpenError("open")

    def record_success(self, key: CircuitKey) -> None:
        self.successes += 1

    def record_failure(self, key: CircuitKey) -> None:
        self.failures += 1


class FailingAuditService:
    def record(self, event: AuditEvent) -> None:
        raise RuntimeError("audit unavailable")


def runtime_context() -> InvocationContext:
    return InvocationContext(
        task_id="task-001",
        trace_id="trace-001",
        span_id="skill-span",
        skill_id="local/demo@0.2.0",
    )


def request() -> MCPRequest:
    return MCPRequest(
        server_name="knowledge-server",
        tool_name="knowledge.query",
        arguments={"query": "framework"},
        runtime_context=runtime_context(),
        timeout=2.0,
    )


def response(*, success: bool = True) -> MCPResponse:
    return MCPResponse(
        success=success,
        content={"result": "ok"} if success else None,
        error_code=None if success else "SHF-MCP-CLIENT-TIMEOUT",
        message="ok" if success else "timeout",
        server_name="knowledge-server",
        tool_name="knowledge.query",
        trace_id="trace-001",
        span_id="skill-span",
        duration_ms=1.0,
        attempts=1,
    )


def context() -> ServiceCallContext:
    return ServiceCallContext(
        runtime_context=runtime_context(),
        service_name="knowledge-service",
        operation_name="query",
        service_span_id="service-span",
        parent_span_id="skill-span",
        request_metadata={"document_id": "doc-001"},
    )


def policy(
    *, audit_policy: AuditPolicy | None = None
) -> ServiceCallPolicy:
    return ServiceCallPolicy(
        operation_type=OperationType.READ,
        idempotency=Idempotency.IDEMPOTENT,
        retry_policy=RetryPolicy(
            max_attempts=2,
            initial_delay_seconds=0,
            max_delay_seconds=0,
            backoff_multiplier=1,
            retryable_error_codes=frozenset(
                {"SHF-MCP-CLIENT-TIMEOUT"}
            ),
        ),
        circuit_policy=CircuitCallPolicy(
            failure_error_codes=frozenset(
                {"SHF-MCP-CLIENT-TIMEOUT"}
            )
        ),
        audit_policy=audit_policy or AuditPolicy(),
        timeout_budget=3.0,
    )


class ServiceCallExecutorTests(unittest.TestCase):
    def build_executor(
        self,
        mcp_client,
        retry_executor,
        circuit_breaker,
        *,
        audit_service=None,
    ) -> ServiceCallExecutor:
        return ServiceCallExecutor(
            mcp_client=mcp_client,
            audit_service=audit_service or InMemoryAuditService(),
            retry_executor=retry_executor,
            circuit_breaker=circuit_breaker,
            clock=FakeClock(),
            config=GovernanceConfig(),
        )

    def test_circuit_retry_mcp_order_and_success_audit(self) -> None:
        events: list[str] = []
        audit = InMemoryAuditService()
        client = RecordingMCPClient(events, response())
        retry = RecordingRetryExecutor(events)
        circuit = RecordingCircuitBreaker(events)
        executor = self.build_executor(
            client, retry, circuit, audit_service=audit
        )

        result = executor.execute(request(), context(), policy())

        self.assertTrue(result.success)
        self.assertEqual(events, ["circuit", "retry", "mcp"])
        self.assertEqual(circuit.successes, 1)
        self.assertEqual(circuit.failures, 0)
        self.assertIsInstance(executor, ServiceCallExecutorProtocol)
        self.assertEqual(
            [event.metadata["event_type"] for event in audit.events()],
            ["SERVICE_CALL_STARTED", "SERVICE_CALL_SUCCEEDED"],
        )
        self.assertNotEqual(
            audit.events()[0].metadata["event_id"],
            audit.events()[1].metadata["event_id"],
        )

    def test_open_circuit_does_not_call_retry_or_mcp(self) -> None:
        events: list[str] = []
        audit = InMemoryAuditService()
        client = RecordingMCPClient(events, response())
        retry = RecordingRetryExecutor(events)
        circuit = RecordingCircuitBreaker(events, opened=True)
        executor = self.build_executor(
            client, retry, circuit, audit_service=audit
        )

        result = executor.execute(request(), context(), policy())

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, CIRCUIT_OPEN)
        self.assertEqual(events, ["circuit"])
        self.assertEqual(client.calls, 0)
        self.assertEqual(retry.calls, 0)
        self.assertEqual(
            [event.metadata["event_type"] for event in audit.events()],
            ["SERVICE_CALL_STARTED", "SERVICE_CALL_FAILED"],
        )

    def test_final_failure_counts_circuit_once(self) -> None:
        events: list[str] = []
        failed = replace(response(success=False), attempts=2)
        client = RecordingMCPClient(events, failed)
        retry = RecordingRetryExecutor(events)
        circuit = RecordingCircuitBreaker(events)
        executor = self.build_executor(client, retry, circuit)

        result = executor.execute(request(), context(), policy())

        self.assertFalse(result.success)
        self.assertEqual(circuit.failures, 1)
        self.assertEqual(
            result.metadata["governance_error"],
            "SHF-SVC-GOV-RETRY_EXHAUSTED",
        )

    def test_non_blocking_audit_failure_is_returned_in_metadata(self) -> None:
        events: list[str] = []
        executor = self.build_executor(
            RecordingMCPClient(events, response()),
            RecordingRetryExecutor(events),
            RecordingCircuitBreaker(events),
            audit_service=FailingAuditService(),
        )

        result = executor.execute(request(), context(), policy())

        self.assertTrue(result.success)
        self.assertEqual(len(result.metadata["audit_errors"]), 2)

    def test_blocking_audit_failure_is_not_swallowed(self) -> None:
        events: list[str] = []
        executor = self.build_executor(
            RecordingMCPClient(events, response()),
            RecordingRetryExecutor(events),
            RecordingCircuitBreaker(events),
            audit_service=FailingAuditService(),
        )
        blocking = AuditPolicy(failure_mode=AuditFailureMode.BLOCKING)

        with self.assertRaisesRegex(RuntimeError, "audit unavailable"):
            executor.execute(request(), context(), policy(audit_policy=blocking))

        self.assertEqual(events, [])

    def test_execution_exception_is_converted(self) -> None:
        events: list[str] = []
        circuit = RecordingCircuitBreaker(events)
        executor = self.build_executor(
            RaisingMCPClient(events, response()),
            RecordingRetryExecutor(events),
            circuit,
        )

        result = executor.execute(request(), context(), policy())

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, EXECUTION_FAILED)
        self.assertEqual(circuit.failures, 1)

    def test_invalid_context_is_converted_without_calling_dependencies(self) -> None:
        events: list[str] = []
        client = RecordingMCPClient(events, response())
        retry = RecordingRetryExecutor(events)
        circuit = RecordingCircuitBreaker(events)
        executor = self.build_executor(client, retry, circuit)

        result = executor.execute(request(), object(), policy())  # type: ignore[arg-type]

        self.assertEqual(result.error_code, CONTEXT_INVALID)
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
