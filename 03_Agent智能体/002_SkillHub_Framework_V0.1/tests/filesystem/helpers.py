from pathlib import Path
from typing import Any, Mapping

from app.mcp_servers.filesystem import FileSystemMCPServerAdapter, FileSystemTools, WorkspacePolicy as ServerWorkspacePolicy
from app.mcp_servers.permissions import InMemoryMCPServerPermissionPolicy
from app.services.audit import InMemoryAuditService
from app.services.filesystem import FilePermission, FileSystemAccessPolicy, FileSystemService, WorkspacePolicy
from app.services.governance import (
    AuditPolicy,
    CircuitCallPolicy,
    GovernanceConfig,
    Idempotency,
    OperationType,
    ServiceCallExecutor,
    ServiceCallPolicy,
)
from app.services.mcp import ConnectionManager, LegacyServerConfigCatalogAdapter, MCPClient, ServerConfig
from app.services.resilience import (
    CircuitBreaker,
    CircuitBreakerPolicy,
    RetryExecutor,
    RetryPolicy,
    SystemClock,
)


SKILL_ID = "local/files@0.2.0"
RETRYABLE_ERRORS = frozenset(
    {"SHF-MCP-CLIENT-TIMEOUT", "SHF-MCP-CLIENT-CONNECTION"}
)


def _policy(
    operation_type: OperationType,
    idempotency: Idempotency,
) -> ServiceCallPolicy:
    max_attempts = 1 if idempotency is Idempotency.NON_IDEMPOTENT else 2
    return ServiceCallPolicy(
        operation_type=operation_type,
        idempotency=idempotency,
        retry_policy=RetryPolicy(
            max_attempts=max_attempts,
            initial_delay_seconds=0,
            max_delay_seconds=0,
            backoff_multiplier=1,
            retryable_error_codes=RETRYABLE_ERRORS,
        ),
        circuit_policy=CircuitCallPolicy(
            failure_error_codes=RETRYABLE_ERRORS
        ),
        audit_policy=AuditPolicy(),
        timeout_budget=30.0,
    )


def filesystem_policies() -> dict[str, ServiceCallPolicy]:
    return {
        "list": _policy(OperationType.READ, Idempotency.IDEMPOTENT),
        "read": _policy(OperationType.READ, Idempotency.IDEMPOTENT),
        "write": _policy(
            OperationType.WRITE, Idempotency.IDEMPOTENT_WITH_KEY
        ),
        "copy": _policy(
            OperationType.WRITE, Idempotency.IDEMPOTENT_WITH_KEY
        ),
        "move": _policy(OperationType.MOVE, Idempotency.NON_IDEMPOTENT),
        "rename": _policy(
            OperationType.MOVE, Idempotency.NON_IDEMPOTENT
        ),
        "archive": _policy(
            OperationType.ARCHIVE, Idempotency.IDEMPOTENT_WITH_KEY
        ),
        "request_delete": _policy(
            OperationType.DELETE, Idempotency.NON_IDEMPOTENT
        ),
        "confirm_delete": _policy(
            OperationType.DELETE, Idempotency.NON_IDEMPOTENT
        ),
    }


class AdapterTransport:
    def __init__(self, adapter: FileSystemMCPServerAdapter) -> None:
        self.adapter = adapter
        self.connected = False
        self.closed = False
        self.last_payload: Mapping[str, Any] | None = None
        self.send_calls = 0

    def connect(self, config: ServerConfig) -> None:
        self.connected = True

    def send(self, payload: Mapping[str, Any], timeout: float) -> Mapping[str, Any]:
        self.send_calls += 1
        self.last_payload = payload
        return self.adapter.handle(payload)

    def close(self) -> None:
        self.closed = True
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected


def build_service(
    root: Path,
    *,
    max_size: int = 1024 * 1024,
    permissions: frozenset[FilePermission] | None = None,
    clock: SystemClock | None = None,
    circuit_breaker: CircuitBreaker | None = None,
):
    tools = FileSystemTools(ServerWorkspacePolicy(root), max_file_size=max_size)
    adapter = FileSystemMCPServerAdapter(
        tools,
        InMemoryMCPServerPermissionPolicy(
            {SKILL_ID: frozenset(item.value for item in FilePermission)}
        ),
    )
    transport = AdapterTransport(adapter)
    manager = ConnectionManager({"adapter": lambda: transport})
    config = ServerConfig(
        server_name="filesystem-server",
        transport_name="adapter",
        allowed_tools=adapter.ALLOWED_TOOLS,
        connect_timeout=1.0,
        max_request_timeout=30.0,
    )
    catalog = LegacyServerConfigCatalogAdapter({"filesystem-server": config})
    client = MCPClient(catalog, catalog, manager)
    audit = InMemoryAuditService()
    governance_clock = clock or SystemClock()
    governance = ServiceCallExecutor(
        mcp_client=client,
        audit_service=audit,
        retry_executor=RetryExecutor(governance_clock),
        circuit_breaker=circuit_breaker
        or CircuitBreaker(
            CircuitBreakerPolicy(
                failure_threshold=2,
                recovery_timeout_seconds=10.0,
            ),
            governance_clock,
        ),
        clock=governance_clock,
        config=GovernanceConfig(),
    )
    grants = permissions or frozenset(FilePermission)
    service = FileSystemService(
        governance,
        FileSystemAccessPolicy({SKILL_ID: grants}),
        WorkspacePolicy(),
        audit,
        filesystem_policies(),
    )
    return service, audit, transport
