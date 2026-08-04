"""可测试的进程内Audit Service实现。"""

from .models import AuditEvent


class InMemoryAuditService:
    """保存脱敏后的事件快照，不写文件或外部系统。"""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self._events.append(event.sanitized())

    def events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)
