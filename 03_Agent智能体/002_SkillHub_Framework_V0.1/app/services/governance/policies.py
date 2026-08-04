"""Service Governance 强类型调用策略。"""

from dataclasses import dataclass
from enum import Enum

from app.services.errors import validate_error_code
from app.services.resilience.retry import RetryPolicy


class OperationType(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    MOVE = "MOVE"
    DELETE = "DELETE"
    ARCHIVE = "ARCHIVE"


class Idempotency(str, Enum):
    IDEMPOTENT = "IDEMPOTENT"
    IDEMPOTENT_WITH_KEY = "IDEMPOTENT_WITH_KEY"
    NON_IDEMPOTENT = "NON_IDEMPOTENT"


class AuditFailureMode(str, Enum):
    BLOCKING = "BLOCKING"
    NON_BLOCKING = "NON_BLOCKING"


@dataclass(frozen=True)
class CircuitCallPolicy:
    enabled: bool = True
    failure_error_codes: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        for error_code in self.failure_error_codes:
            validate_error_code(error_code)


@dataclass(frozen=True)
class AuditPolicy:
    enabled: bool = True
    failure_mode: AuditFailureMode = AuditFailureMode.NON_BLOCKING


@dataclass(frozen=True)
class ServiceCallPolicy:
    operation_type: OperationType
    idempotency: Idempotency
    retry_policy: RetryPolicy
    circuit_policy: CircuitCallPolicy
    audit_policy: AuditPolicy
    timeout_budget: float

    def __post_init__(self) -> None:
        if not isinstance(self.operation_type, OperationType):
            raise ValueError("operation_type必须是OperationType")
        if not isinstance(self.idempotency, Idempotency):
            raise ValueError("idempotency必须是Idempotency")
        if not isinstance(self.retry_policy, RetryPolicy):
            raise ValueError("retry_policy必须是RetryPolicy")
        if not isinstance(self.circuit_policy, CircuitCallPolicy):
            raise ValueError("circuit_policy必须是CircuitCallPolicy")
        if not isinstance(self.audit_policy, AuditPolicy):
            raise ValueError("audit_policy必须是AuditPolicy")
        if self.timeout_budget <= 0:
            raise ValueError("timeout_budget必须大于0")
        if (
            self.idempotency is Idempotency.NON_IDEMPOTENT
            and self.retry_policy.max_attempts != 1
        ):
            raise ValueError("NON_IDEMPOTENT操作禁止自动重试")


@dataclass(frozen=True)
class GovernanceConfig:
    schema_version: str = "0.1"
    audit_error_metadata_key: str = "audit_errors"

    def __post_init__(self) -> None:
        if not self.schema_version.strip():
            raise ValueError("schema_version不能为空")
        if not self.audit_error_metadata_key.strip():
            raise ValueError("audit_error_metadata_key不能为空")
