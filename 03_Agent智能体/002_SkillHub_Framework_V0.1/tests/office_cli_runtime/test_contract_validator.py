import pytest

from app.mcp_servers.office.runtime.mcp_bridge.contract_validator import (
    OfficeCLIContractValidator,
)
from app.mcp_servers.office.runtime.mcp_bridge.transport_errors import (
    OfficeCLIMCPContractError,
)

from .helpers import TOOL_SCHEMA, initialize_result, tools_result


def test_real_contract_shape_is_accepted() -> None:
    contract = OfficeCLIContractValidator().validate(
        initialize_result(), tools_result()
    )
    assert contract.input_schema["properties"]["command"]["type"] == [
        "string",
        "array",
    ]


@pytest.mark.parametrize(
    "schema",
    (
        {"type": "object", "properties": {}, "required": []},
        {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
        {
            **TOOL_SCHEMA,
            "properties": {
                **TOOL_SCHEMA["properties"],
                "dynamic_tool": {"type": "string"},
            },
        },
    ),
)
def test_schema_drift_is_rejected(schema) -> None:
    with pytest.raises(OfficeCLIMCPContractError):
        OfficeCLIContractValidator().validate(
            initialize_result(), tools_result(schema=schema)
        )
