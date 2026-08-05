"""Audit Service依赖接口。"""

from typing import Protocol, runtime_checkable

from .models import AuditEvent


@runtime_checkable
class AuditServiceProtocol(Protocol):
    def record(self, event: AuditEvent) -> None: ...
