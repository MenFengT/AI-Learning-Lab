"""Service Layer有限重试执行器，不属于MCPClient。"""

from dataclasses import dataclass, is_dataclass, replace
from typing import Callable, TypeVar

from app.services.errors import ServiceLayerError

from .clock import ClockProtocol, SystemClock


T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int
    initial_delay_seconds: float
    max_delay_seconds: float
    backoff_multiplier: float
    retryable_error_codes: frozenset[str]

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts必须至少为1")
        if self.initial_delay_seconds < 0:
            raise ValueError("initial_delay_seconds不能小于0")
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ValueError("max_delay_seconds不能小于初始延迟")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier不能小于1")


class RetryExecutor:
    """根据稳定错误码执行有限、指数退避重试。"""

    def __init__(self, clock: ClockProtocol | None = None) -> None:
        self._clock = clock or SystemClock()

    def execute(
        self,
        operation: Callable[[], T],
        policy: RetryPolicy,
        *,
        timeout_seconds: float,
    ) -> T:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds必须大于0")

        started_at = self._clock.now()
        delay = policy.initial_delay_seconds
        attempt = 0
        while attempt < policy.max_attempts:
            attempt += 1
            try:
                outcome = operation()
            except Exception as exc:
                if not self._should_retry_exception(exc, policy):
                    raise
                if not self._can_retry(
                    attempt, policy, started_at, timeout_seconds, delay
                ):
                    raise
                self._clock.sleep(delay)
                delay = min(
                    delay * policy.backoff_multiplier,
                    policy.max_delay_seconds,
                )
                continue

            error_code = self._outcome_error_code(outcome)
            if error_code not in policy.retryable_error_codes:
                return self._with_attempts(outcome, attempt)
            if not self._can_retry(
                attempt, policy, started_at, timeout_seconds, delay
            ):
                return self._with_attempts(outcome, attempt)
            self._clock.sleep(delay)
            delay = min(
                delay * policy.backoff_multiplier,
                policy.max_delay_seconds,
            )

        raise RuntimeError("RetryExecutor进入不可达状态")

    def _can_retry(
        self,
        attempt: int,
        policy: RetryPolicy,
        started_at: float,
        timeout_seconds: float,
        delay: float,
    ) -> bool:
        if attempt >= policy.max_attempts:
            return False
        elapsed = self._clock.now() - started_at
        return elapsed + delay < timeout_seconds

    @staticmethod
    def _should_retry_exception(
        error: Exception, policy: RetryPolicy
    ) -> bool:
        return (
            isinstance(error, ServiceLayerError)
            and error.descriptor.code in policy.retryable_error_codes
        )

    @staticmethod
    def _outcome_error_code(outcome: object) -> str | None:
        success = getattr(outcome, "success", True)
        if success:
            return None
        error_code = getattr(outcome, "error_code", None)
        return error_code if isinstance(error_code, str) else None

    @staticmethod
    def _with_attempts(outcome: T, attempts: int) -> T:
        if is_dataclass(outcome) and hasattr(outcome, "attempts"):
            return replace(outcome, attempts=attempts)
        return outcome
