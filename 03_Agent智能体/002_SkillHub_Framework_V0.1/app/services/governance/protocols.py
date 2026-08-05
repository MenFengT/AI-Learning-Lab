"""Service Governance 的依赖与公开执行协议。"""

from typing import Callable, Protocol, TypeVar, runtime_checkable

from app.services.models import MCPRequest, MCPResponse
from app.services.resilience.circuit_breaker import CircuitKey
from app.services.resilience.retry import RetryPolicy

from .models import ServiceCallContext
from .policies import ServiceCallPolicy


T = TypeVar("T")


@runtime_checkable
class RetryExecutorProtocol(Protocol):
    def execute(
        self,
        operation: Callable[[], T],
        policy: RetryPolicy,
        *,
        timeout_seconds: float,
    ) -> T: ...


@runtime_checkable
class CircuitBreakerProtocol(Protocol):
    def allow_request(self, key: CircuitKey) -> None: ...

    def record_success(self, key: CircuitKey) -> None: ...

    def record_failure(self, key: CircuitKey) -> None: ...


@runtime_checkable
class GovernanceConfigProtocol(Protocol):
    schema_version: str
    audit_error_metadata_key: str


@runtime_checkable
class ServiceCallExecutorProtocol(Protocol):
    def execute(
        self,
        request: MCPRequest,
        context: ServiceCallContext,
        policy: ServiceCallPolicy,
    ) -> MCPResponse: ...
