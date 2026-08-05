"""OfficeCLI 1.0.143真实MCP契约校验。"""

from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from .transport_errors import OfficeCLIMCPContractError


@dataclass(frozen=True)
class OfficeCLIServerContract:
    server_name: str
    server_version: str
    protocol_version: str
    tools_list_changed: bool
    tool_name: str
    input_schema: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "input_schema",
            MappingProxyType(deepcopy(dict(self.input_schema))),
        )


class OfficeCLIContractValidator:
    def __init__(
        self,
        *,
        expected_server_name: str = "officecli",
        expected_server_version: str = "1.0.143",
        expected_protocol_version: str = "2024-11-05",
    ) -> None:
        self._server_name = expected_server_name
        self._server_version = expected_server_version
        self._protocol_version = expected_protocol_version

    def validate(
        self,
        initialize_result: Any,
        tools_result: Any,
    ) -> OfficeCLIServerContract:
        server_info = _attribute(initialize_result, "serverInfo", "server_info")
        server_name = _text_attribute(server_info, "name")
        server_version = _text_attribute(server_info, "version")
        protocol_version = str(
            _attribute(initialize_result, "protocolVersion", "protocol_version")
        )
        capabilities = _attribute(initialize_result, "capabilities")
        tool_capability = _attribute(capabilities, "tools")
        list_changed = bool(
            _attribute(tool_capability, "listChanged", "list_changed")
        )
        tools = tuple(_attribute(tools_result, "tools"))
        if len(tools) != 1:
            raise OfficeCLIMCPContractError("OfficeCLI必须只暴露一个Tool")
        tool = tools[0]
        tool_name = _text_attribute(tool, "name")
        schema = _mapping(_attribute(tool, "inputSchema", "input_schema"))

        if server_name != self._server_name:
            raise OfficeCLIMCPContractError("OfficeCLI Server name不匹配")
        if server_version != self._server_version:
            raise OfficeCLIMCPContractError("OfficeCLI Server version不匹配")
        if protocol_version != self._protocol_version:
            raise OfficeCLIMCPContractError("OfficeCLI protocolVersion不匹配")
        if list_changed:
            raise OfficeCLIMCPContractError("OfficeCLI Tool列表必须固定")
        if tool_name != "officecli":
            raise OfficeCLIMCPContractError("OfficeCLI Tool名称不匹配")
        _validate_schema(schema)
        return OfficeCLIServerContract(
            server_name,
            server_version,
            protocol_version,
            list_changed,
            tool_name,
            schema,
        )


def _validate_schema(schema: Mapping[str, Any]) -> None:
    if schema.get("type") != "object":
        raise OfficeCLIMCPContractError("OfficeCLI inputSchema必须是object")
    properties = _mapping(schema.get("properties"))
    if set(properties) != {"command"}:
        raise OfficeCLIMCPContractError("OfficeCLI只能包含command参数")
    command = _mapping(properties["command"])
    command_types = command.get("type")
    if not isinstance(command_types, list) or set(command_types) != {
        "string",
        "array",
    }:
        raise OfficeCLIMCPContractError("OfficeCLI command类型不匹配")
    items = _mapping(command.get("items"))
    if items.get("type") != "string":
        raise OfficeCLIMCPContractError("OfficeCLI command数组元素必须是string")
    required = schema.get("required")
    if not isinstance(required, list) or required != ["command"]:
        raise OfficeCLIMCPContractError("OfficeCLI command必须是必需参数")


def _attribute(value: Any, *names: str) -> Any:
    for name in names:
        if hasattr(value, name):
            return getattr(value, name)
        if isinstance(value, Mapping) and name in value:
            return value[name]
    raise OfficeCLIMCPContractError(f"MCP契约缺少字段：{names[0]}")


def _text_attribute(value: Any, *names: str) -> str:
    item = _attribute(value, *names)
    if not isinstance(item, str) or not item.strip():
        raise OfficeCLIMCPContractError(f"MCP字段无效：{names[0]}")
    return item.strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OfficeCLIMCPContractError("MCP Schema字段必须是Mapping")
    return value
