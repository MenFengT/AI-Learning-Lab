"""Resilience组件使用的可替换时钟。"""

from time import monotonic, sleep
from typing import Protocol, runtime_checkable


@runtime_checkable
class ClockProtocol(Protocol):
    def now(self) -> float: ...

    def sleep(self, seconds: float) -> None: ...


class SystemClock:
    """生产环境单调时钟；测试应注入Fake Clock。"""

    def now(self) -> float:
        return monotonic()

    def sleep(self, seconds: float) -> None:
        sleep(seconds)
