"""施工文档 Demo 输出契约。"""

from dataclasses import dataclass

from app.artifact.models import Artifact
from app.runtime.invocation_context import InvocationContext
from app.services.audit.models import AuditEvent


@dataclass(frozen=True)
class ConstructionDemoResult:
    artifact: Artifact
    runtime_context: InvocationContext
    knowledge_document_ids: tuple[str, ...]
    generated_content: str
    audit_events: tuple[AuditEvent, ...]
