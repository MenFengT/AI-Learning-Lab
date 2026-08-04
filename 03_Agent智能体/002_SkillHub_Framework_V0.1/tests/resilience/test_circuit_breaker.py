import unittest

from app.services.resilience import (
    CircuitBreaker,
    CircuitBreakerPolicy,
    CircuitKey,
    CircuitOpenError,
    CircuitState,
)


class FakeClock:
    def __init__(self) -> None:
        self.current = 0.0

    def now(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current += seconds

    def advance(self, seconds: float) -> None:
        self.current += seconds


class CircuitBreakerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.breaker = CircuitBreaker(
            CircuitBreakerPolicy(
                failure_threshold=2,
                recovery_timeout_seconds=5.0,
            ),
            self.clock,
        )
        self.key = CircuitKey("office-server", "read-document")

    def test_closed_open_half_open_closed_transitions(self) -> None:
        self.assertEqual(self.breaker.state(self.key), CircuitState.CLOSED)
        self.breaker.record_failure(self.key)
        self.assertEqual(self.breaker.state(self.key), CircuitState.CLOSED)
        self.breaker.record_failure(self.key)
        self.assertEqual(self.breaker.state(self.key), CircuitState.OPEN)

        self.clock.advance(5.0)
        self.breaker.allow_request(self.key)
        self.assertEqual(self.breaker.state(self.key), CircuitState.HALF_OPEN)

        self.breaker.record_success(self.key)
        self.assertEqual(self.breaker.state(self.key), CircuitState.CLOSED)

    def test_open_state_fails_fast(self) -> None:
        self.breaker.record_failure(self.key)
        self.breaker.record_failure(self.key)

        with self.assertRaises(CircuitOpenError):
            self.breaker.allow_request(self.key)

    def test_half_open_failure_reopens_circuit(self) -> None:
        self.breaker.record_failure(self.key)
        self.breaker.record_failure(self.key)
        self.clock.advance(5.0)
        self.breaker.allow_request(self.key)

        self.breaker.record_failure(self.key)

        self.assertEqual(self.breaker.state(self.key), CircuitState.OPEN)
        with self.assertRaises(CircuitOpenError):
            self.breaker.allow_request(self.key)

    def test_circuits_are_isolated_by_server_and_tool(self) -> None:
        other = CircuitKey("filesystem-server", "read-file")
        self.breaker.record_failure(self.key)
        self.breaker.record_failure(self.key)

        self.assertEqual(self.breaker.state(self.key), CircuitState.OPEN)
        self.assertEqual(self.breaker.state(other), CircuitState.CLOSED)
        self.breaker.allow_request(other)


if __name__ == "__main__":
    unittest.main()
