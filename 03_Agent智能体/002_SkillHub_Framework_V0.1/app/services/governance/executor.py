"""组合熔断、重试、MCP与审计的统一Service调用执行器。"""

from dataclasses import replace
from typing import Any, Mapping
from uuid import uuid4

from app.services.audit.models import AuditEvent
from app.services.audit.protocols import AuditServiceProtocol
from app.services.mcp.protocols import MCPClientProtocol
from app.services.models import MCPRequest, MCPResponse
from app.services.resilience.circuit_breaker import CircuitKey, CircuitOpenError
from app.services.resilience.clock import ClockProtocol

from .errors import (
    CIRCUIT_OPEN,
    CONTEXT_INVALID,
    EXECUTION_FAILED,
    POLICY_INVALID,
    RETRY_EXHAUSTED,
    TIME_BUDGET_EXCEEDED,
)
from .models import ServiceCallContext, ServiceCallEventType
from .policies import AuditFailureMode, ServiceCallPolicy
from .protocols import (
    CircuitBreakerProtocol,
    GovernanceConfigProtocol,
    RetryExecutorProtocol,
)


class ServiceCallExecutor:
    """执行基础设施治理，不解释或修改业务参数与业务结果。"""

    def __init__(
        self,
        mcp_client: MCPClientProtocol,
        audit_service: AuditServiceProtocol,
        retry_executor: RetryExecutorProtocol,
        circuit_breaker: CircuitBreakerProtocol,
        clock: ClockProtocol,
        config: GovernanceConfigProtocol,
    ) -> None:
        self._mcp_client = mcp_client
        self._audit_service = audit_service
        self._retry_executor = retry_executor
        self._circuit_breaker = circuit_breaker
        self._clock = clock
        self._config = config

    def execute(
        self,
        request: MCPRequest,
        context: ServiceCallContext,
        policy: ServiceCallPolicy,
    ) -> MCPResponse:
        started_at = self._clock.now()
        if not isinstance(context, ServiceCallContext):
            return self._failure_response(
                request,
                CONTEXT_INVALID,
                "Service调用上下文无效",
                started_at,
            )
        if not isinstance(policy, ServiceCallPolicy):
            return self._failure_response(
                request,
                POLICY_INVALID,
                "Service调用策略无效",
                started_at,
            )
        audit_errors: list[dict[str, str]] = []
        self._audit(
            ServiceCallEventType.SERVICE_CALL_STARTED,
            request,
            context,
            policy,
            started_at,
            None,
            audit_errors,
        )

        key = CircuitKey(request.server_name, request.tool_name)
        try:
            if policy.circuit_policy.enabled:
                self._circuit_breaker.allow_request(key)
        except CircuitOpenError:
            response = self._failure_response(
                request,
                CIRCUIT_OPEN,
                "Service调用被熔断器拒绝",
                started_at,
            )
            return self._finish_failure(
                response, request, context, policy, started_at, audit_errors
            )

        try:
            response = self._retry_executor.execute(
                lambda: self._mcp_client.call(request),
                policy.retry_policy,
                timeout_seconds=policy.timeout_budget,
            )
        except Exception as exc:
            if policy.circuit_policy.enabled:
                self._circuit_breaker.record_failure(key)
            response = self._failure_response(
                request,
                EXECUTION_FAILED,
                "Service基础设施调用失败",
                started_at,
                {"exception_type": type(exc).__name__},
            )
            return self._finish_failure(
                response, request, context, policy, started_at, audit_errors
            )

        if response.success:
            if policy.circuit_policy.enabled:
                self._circuit_breaker.record_success(key)
            self._audit(
                ServiceCallEventType.SERVICE_CALL_SUCCEEDED,
                request,
                context,
                policy,
                started_at,
                None,
                audit_errors,
            )
            return self._with_governance_metadata(response, audit_errors)

        if (
            policy.circuit_policy.enabled
            and response.error_code
            in policy.circuit_policy.failure_error_codes
        ):
            self._circuit_breaker.record_failure(key)
        response = self._classify_retry_failure(
            response, policy, started_at
        )
        return self._finish_failure(
            response, request, context, policy, started_at, audit_errors
        )

    def _finish_failure(
        self,
        response: MCPResponse,
        request: MCPRequest,
        context: ServiceCallContext,
        policy: ServiceCallPolicy,
        started_at: float,
        audit_errors: list[dict[str, str]],
    ) -> MCPResponse:
        self._audit(
            ServiceCallEventType.SERVICE_CALL_FAILED,
            request,
            context,
            policy,
            started_at,
            response.error_code,
            audit_errors,
        )
        return self._with_governance_metadata(response, audit_errors)

    def _audit(
        self,
        event_type: ServiceCallEventType,
        request: MCPRequest,
        context: ServiceCallContext,
        policy: ServiceCallPolicy,
        started_at: float,
        error_code: str | None,
        audit_errors: list[dict[str, str]],
    ) -> None:
        if not policy.audit_policy.enabled:
            return
        event = AuditEvent(
            task_id=context.runtime_context.task_id,
            trace_id=context.runtime_context.trace_id,
            span_id=context.service_span_id,
            skill_id=context.runtime_context.skill_id,
            server=request.server_name,
            tool=request.tool_name,
            duration=max(0.0, self._clock.now() - started_at),
            error_code=error_code,
            metadata={
                "event_id": uuid4().hex,
                "event_type": event_type.value,
                "service_name": context.service_name,
                "operation_name": context.operation_name,
                "parent_span_id": context.parent_span_id,
                "request_metadata": _to_plain_value(
                    context.request_metadata
                ),
                "schema_version": self._config.schema_version,
            },
        )
        try:
            self._audit_service.record(event)
        except Exception as exc:
            if policy.audit_policy.failure_mode is AuditFailureMode.BLOCKING:
                raise
            audit_errors.append(
                {
                    "event_type": event_type.value,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

    def _classify_retry_failure(
        self,
        response: MCPResponse,
        policy: ServiceCallPolicy,
        started_at: float,
    ) -> MCPResponse:
        if response.error_code not in policy.retry_policy.retryable_error_codes:
            return response
        metadata = dict(response.metadata)
        if response.attempts >= policy.retry_policy.max_attempts:
            metadata["governance_error"] = RETRY_EXHAUSTED
        else:
            metadata["governance_error"] = TIME_BUDGET_EXCEEDED
        return replace(response, metadata=metadata)

    def _failure_response(
        self,
        request: MCPRequest,
        error_code: str,
        message: str,
        started_at: float,
        metadata: dict[str, Any] | None = None,
    ) -> MCPResponse:
        return MCPResponse(
            success=False,
            content=None,
            error_code=error_code,
            message=message,
            server_name=request.server_name,
            tool_name=request.tool_name,
            trace_id=request.runtime_context.trace_id,
            span_id=request.runtime_context.span_id,
            duration_ms=max(0.0, self._clock.now() - started_at) * 1000,
            attempts=1,
            metadata=metadata or {},
        )

    def _with_governance_metadata(
        self,
        response: MCPResponse,
        audit_errors: list[dict[str, str]],
    ) -> MCPResponse:
        if not audit_errors:
            return response
        metadata = dict(response.metadata)
        metadata[self._config.audit_error_metadata_key] = tuple(audit_errors)
        return replace(response, metadata=metadata)


def _to_plain_value(value: Any) -> Any:
    """将只读Context快照转换为AuditEvent可深拷贝的基础容器。"""
    if isinstance(value, Mapping):
        return {
            str(key): _to_plain_value(child)
            for key, child in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(_to_plain_value(child) for child in value)
    return value
