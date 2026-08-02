"""定义任务生命周期状态与合法状态迁移。"""

from dataclasses import dataclass, field
from enum import Enum


class LifecycleStatus(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


ALLOWED_TRANSITIONS: dict[LifecycleStatus, frozenset[LifecycleStatus]] = {
    LifecycleStatus.CREATED: frozenset(
        {LifecycleStatus.PLANNING, LifecycleStatus.FAILED}
    ),
    LifecycleStatus.PLANNING: frozenset(
        {LifecycleStatus.EXECUTING, LifecycleStatus.FAILED}
    ),
    LifecycleStatus.EXECUTING: frozenset(
        {LifecycleStatus.COMPLETED, LifecycleStatus.FAILED}
    ),
    LifecycleStatus.COMPLETED: frozenset(),
    LifecycleStatus.FAILED: frozenset(),
}


@dataclass
class Lifecycle:
    """维护一次任务的当前状态和完整状态历史。"""

    status: LifecycleStatus = LifecycleStatus.CREATED
    history: list[LifecycleStatus] = field(
        default_factory=lambda: [LifecycleStatus.CREATED]
    )

    def transition_to(self, next_status: LifecycleStatus) -> None:
        if next_status not in ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(
                f"非法生命周期迁移：{self.status.value} -> {next_status.value}"
            )
        self.status = next_status
        self.history.append(next_status)
