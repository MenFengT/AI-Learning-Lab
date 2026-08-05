"""MCP Server Registry进程内Descriptor存储。"""

from .exceptions import DescriptorValidationError, ServerNotFoundError
from .models import MCPServerDescriptor


class InMemoryMCPServerStore:
    """只保存不可变MCPServerDescriptor，不保存连接或Transport。"""

    def __init__(self) -> None:
        self._descriptors: dict[str, MCPServerDescriptor] = {}

    def add(self, descriptor: MCPServerDescriptor) -> None:
        if not isinstance(descriptor, MCPServerDescriptor):
            raise DescriptorValidationError(
                "Store只能保存MCPServerDescriptor"
            )
        self._descriptors[descriptor.server_id] = descriptor

    def remove(self, server_id: str) -> MCPServerDescriptor:
        try:
            return self._descriptors.pop(server_id)
        except KeyError as exc:
            raise ServerNotFoundError(f"Server不存在：{server_id}") from exc

    def get_by_id(self, server_id: str) -> MCPServerDescriptor | None:
        return self._descriptors.get(server_id)

    def list_all(self) -> tuple[MCPServerDescriptor, ...]:
        return tuple(
            sorted(self._descriptors.values(), key=lambda item: item.server_id)
        )
