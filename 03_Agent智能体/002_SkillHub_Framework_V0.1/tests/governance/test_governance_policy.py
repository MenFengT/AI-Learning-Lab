import unittest

from app.services.governance import (
    AuditPolicy,
    CircuitCallPolicy,
    Idempotency,
    OperationType,
    ServiceCallPolicy,
)
from app.services.resilience import RetryPolicy


def retry_policy(max_attempts: int = 2) -> RetryPolicy:
    return RetryPolicy(
        max_attempts=max_attempts,
        initial_delay_seconds=0.1,
        max_delay_seconds=1.0,
        backoff_multiplier=2.0,
        retryable_error_codes=frozenset({"SHF-MCP-CLIENT-TIMEOUT"}),
    )


class GovernancePolicyTests(unittest.TestCase):
    def test_policy_contains_all_governance_dimensions(self) -> None:
        policy = ServiceCallPolicy(
            operation_type=OperationType.READ,
            idempotency=Idempotency.IDEMPOTENT,
            retry_policy=retry_policy(),
            circuit_policy=CircuitCallPolicy(
                failure_error_codes=frozenset(
                    {"SHF-MCP-CLIENT-TIMEOUT"}
                )
            ),
            audit_policy=AuditPolicy(),
            timeout_budget=5.0,
        )

        self.assertEqual(policy.operation_type, OperationType.READ)
        self.assertEqual(policy.timeout_budget, 5.0)

    def test_non_idempotent_operation_cannot_retry(self) -> None:
        with self.assertRaisesRegex(ValueError, "禁止自动重试"):
            ServiceCallPolicy(
                operation_type=OperationType.DELETE,
                idempotency=Idempotency.NON_IDEMPOTENT,
                retry_policy=retry_policy(max_attempts=2),
                circuit_policy=CircuitCallPolicy(),
                audit_policy=AuditPolicy(),
                timeout_budget=5.0,
            )

    def test_invalid_timeout_and_error_code_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "timeout_budget"):
            ServiceCallPolicy(
                operation_type=OperationType.READ,
                idempotency=Idempotency.IDEMPOTENT,
                retry_policy=retry_policy(),
                circuit_policy=CircuitCallPolicy(),
                audit_policy=AuditPolicy(),
                timeout_budget=0,
            )
        with self.assertRaises(ValueError):
            CircuitCallPolicy(failure_error_codes=frozenset({"TIMEOUT"}))


if __name__ == "__main__":
    unittest.main()
