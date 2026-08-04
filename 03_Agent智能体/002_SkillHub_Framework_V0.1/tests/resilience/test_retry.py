import unittest

from app.services import MCPResponse
from app.services.resilience import RetryExecutor, RetryPolicy


class FakeClock:
    def __init__(self) -> None:
        self.current = 0.0
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.current += seconds


def response(success: bool, error_code: str | None = None) -> MCPResponse:
    return MCPResponse(
        success=success,
        content="ok" if success else None,
        error_code=error_code,
        message="ok" if success else "failed",
        server_name="office-server",
        tool_name="read-document",
        trace_id="trace-001",
        span_id="span-001",
        duration_ms=1.0,
        attempts=1,
    )


def policy(max_attempts: int = 3) -> RetryPolicy:
    return RetryPolicy(
        max_attempts=max_attempts,
        initial_delay_seconds=1.0,
        max_delay_seconds=4.0,
        backoff_multiplier=2.0,
        retryable_error_codes=frozenset(
            {
                "SHF-MCP-CLIENT-TIMEOUT",
                "SHF-MCP-CLIENT-CONNECTION",
            }
        ),
    )


class RetryTests(unittest.TestCase):
    def test_retryable_error_uses_exponential_backoff(self) -> None:
        clock = FakeClock()
        outcomes = [
            response(False, "SHF-MCP-CLIENT-TIMEOUT"),
            response(False, "SHF-MCP-CLIENT-CONNECTION"),
            response(True),
        ]
        calls = 0

        def operation() -> MCPResponse:
            nonlocal calls
            result = outcomes[calls]
            calls += 1
            return result

        result = RetryExecutor(clock).execute(
            operation, policy(), timeout_seconds=10.0
        )

        self.assertTrue(result.success)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(calls, 3)
        self.assertEqual(clock.sleeps, [1.0, 2.0])

    def test_non_retryable_error_returns_immediately(self) -> None:
        clock = FakeClock()
        calls = 0

        def operation() -> MCPResponse:
            nonlocal calls
            calls += 1
            return response(False, "SHF-MCP-TOOL-PERMISSION_DENIED")

        result = RetryExecutor(clock).execute(
            operation, policy(), timeout_seconds=10.0
        )

        self.assertEqual(calls, 1)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(clock.sleeps, [])

    def test_maximum_attempts_are_enforced(self) -> None:
        clock = FakeClock()
        calls = 0

        def operation() -> MCPResponse:
            nonlocal calls
            calls += 1
            return response(False, "SHF-MCP-CLIENT-TIMEOUT")

        result = RetryExecutor(clock).execute(
            operation, policy(max_attempts=3), timeout_seconds=20.0
        )

        self.assertEqual(calls, 3)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(clock.sleeps, [1.0, 2.0])

    def test_timeout_budget_prevents_additional_attempt(self) -> None:
        clock = FakeClock()
        calls = 0

        def operation() -> MCPResponse:
            nonlocal calls
            calls += 1
            return response(False, "SHF-MCP-CLIENT-TIMEOUT")

        result = RetryExecutor(clock).execute(
            operation, policy(), timeout_seconds=1.0
        )

        self.assertEqual(calls, 1)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(clock.sleeps, [])


if __name__ == "__main__":
    unittest.main()
