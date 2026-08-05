from app.mcp_registry import (
    MCPServerDescriptor,
    ServerCapabilities,
    ServerHealthStatus,
    ToolDescriptor,
    ToolIdempotency,
    TransportType,
    build_server_id,
)


def tool(
    name: str = "knowledge.query",
    *,
    permission: str = "KNOWLEDGE_READ",
) -> ToolDescriptor:
    return ToolDescriptor(
        tool_name=name,
        description="固定MCP Tool",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
        },
        output_schema={"type": "object"},
        permission_required=permission,
        idempotency=ToolIdempotency.IDEMPOTENT,
    )


def descriptor(
    *,
    server_name: str = "knowledge-server",
    version: str = "0.2.0",
    enabled: bool = True,
    health: ServerHealthStatus = ServerHealthStatus.HEALTHY,
    tools: tuple[ToolDescriptor, ...] | None = None,
    metadata: dict | None = None,
) -> MCPServerDescriptor:
    selected_tools = tools if tools is not None else (tool(),)
    return MCPServerDescriptor(
        server_id=build_server_id(server_name, version),
        server_name=server_name,
        version=version,
        description="受控MCP Server",
        transport_type=TransportType.IN_MEMORY,
        transport_config_reference=f"mcp.{server_name}.local",
        capabilities=ServerCapabilities(tools=True),
        allowed_tools=selected_tools,
        health_status=health,
        enabled=enabled,
        metadata=metadata or {"owner": "framework"},
    )
