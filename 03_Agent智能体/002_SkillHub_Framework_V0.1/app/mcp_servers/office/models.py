"""Office MCP Server固定Tool与CLI端口模型。"""

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class OfficeToolDefinition:
    name: str
    description: str
    input_schema: Mapping[str, str]
    output_schema: Mapping[str, str]
    permission: str


class OfficeCLIAdapterProtocol(Protocol):
    """OfficeCLI唯一受控适配端口，由Composition Root注入实现。"""

    def create_document(
        self, arguments: Mapping[str, Any], runtime_context: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...

    def update_document(
        self, arguments: Mapping[str, Any], runtime_context: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...

    def convert_document(
        self, arguments: Mapping[str, Any], runtime_context: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...

    def export_document(
        self, arguments: Mapping[str, Any], runtime_context: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...
