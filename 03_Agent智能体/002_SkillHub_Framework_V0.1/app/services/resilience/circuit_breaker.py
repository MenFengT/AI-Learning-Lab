"""按MCP Server和Tool隔离的Service Layer熔断器。"""

from dataclasses import dataclass
from enum import Enum

from .clock import ClockProtocol, SystemClock


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass(frozen=True)
class CircuitKey:
    server_name: str
    tool_name: str

    def __post_init__(self) -> None:
        if not self.server_name.strip() or not self.tool_name.strip():
            raise ValueError("server_name和tool_name不能为空")


@dataclass(frozen=True)
class CircuitBreakerPolicy:
    failure_threshold: int
    recovery_timeout_seconds: float
    half_open_success_threshold: int = 1

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold必须至少为1")
        if self.recovery_timeout_seconds <= 0:
            raise ValueError("recovery_timeout_seconds必须大于0")
        if self.half_open_success_threshold < 1:
            raise ValueError("half_open_success_threshold必须至少为1")


class CircuitOpenError(Exception):
    """熔断OPEN时的快速失败。"""

    error_code = "SHF-SVC-CIRCUIT-OPEN"


@dataclass
class _CircuitRecord:
    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    half_open_successes: int = 0
    opened_at: float | None = None


class CircuitBreaker:
    """只管理弹性状态，不调用MCPClient或感知Skill。"""

    def __init__(
        self,
        policy: CircuitBreakerPolicy,
        clock: ClockProtocol | None = None,
    ) -> None:
        self._policy = policy
        self._clock = clock or SystemClock()
        self._records: dict[CircuitKey, _CircuitRecord] = {}

    def allow_request(self, key: CircuitKey) -> None:
        record = self._record(key)
        if record.state is not CircuitState.OPEN:
            return
        if record.opened_at is None:
            raise CircuitOpenError(f"熔断器已打开：{key}")
        if (
            self._clock.now() - record.opened_at
            < self._policy.recovery_timeout_seconds
        ):
            raise CircuitOpenError(f"熔断器已打开：{key}")
        record.state = CircuitState.HALF_OPEN
        record.half_open_successes = 0

    def record_success(self, key: CircuitKey) -> None:
        record = self._record(key)
        if record.state is CircuitState.HALF_OPEN:
            record.half_open_successes += 1
            if (
                record.half_open_successes
                >= self._policy.half_open_success_threshold
            ):
                self._close(record)
            return
        if record.state is CircuitState.CLOSED:
            record.failures = 0

    def record_failure(self, key: CircuitKey) -> None:
        record = self._record(key)
        if record.state is CircuitState.HALF_OPEN:
            self._open(record)
            return
        if record.state is CircuitState.OPEN:
            return
        record.failures += 1
        if record.failures >= self._policy.failure_threshold:
            self._open(record)

    def state(self, key: CircuitKey) -> CircuitState:
        return self._record(key).state

    def _record(self, key: CircuitKey) -> _CircuitRecord:
        return self._records.setdefault(key, _CircuitRecord())

    def _open(self, record: _CircuitRecord) -> None:
        record.state = CircuitState.OPEN
        record.opened_at = self._clock.now()
        record.half_open_successes = 0

    @staticmethod
    def _close(record: _CircuitRecord) -> None:
        record.state = CircuitState.CLOSED
        record.failures = 0
        record.half_open_successes = 0
        record.opened_at = None
