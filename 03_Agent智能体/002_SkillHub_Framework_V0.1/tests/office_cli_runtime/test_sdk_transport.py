from types import SimpleNamespace

import pytest

from app.mcp_servers.office.runtime.mcp_bridge.capability_mapper import (
    OfficeCLICapabilityMapper,
)
from app.mcp_servers.office.runtime.mcp_bridge.capability_policy import (
    OfficeCLICapabilityPolicy,
)
from app.mcp_servers.office.runtime.mcp_bridge.mapping_models import (
    OfficeCapability,
    OfficeCapabilityRequest,
    OfficeDocumentContent,
)
from app.mcp_servers.office.runtime.mcp_bridge.sdk_provider import (
    OfficeCLIMCPTransportProvider,
)
from app.mcp_servers.office.runtime.mcp_bridge.sdk_transport import (
    OfficeCLIMCPTransportConfig,
)
from app.mcp_servers.office.runtime.mcp_bridge.transport_errors import (
    OfficeCLIMCPCallError,
    OfficeCLIMCPContractError,
    OfficeCLIMCPRequestError,
    OfficeCLIMCPTimeoutError,
)

from .helpers import FakeSDK, FakeSession, initialize_result


EXECUTABLE = "C:/Users/MF/AppData/Local/OfficeCLI/officecli.exe"


def _call():
    plan = OfficeCLICapabilityMapper(OfficeCLICapabilityPolicy()).map(
        OfficeCapabilityRequest(
            OfficeCapability.CREATE_DOCUMENT,
            "task-001",
            "方案.docx",
            OfficeDocumentContent("地下室防水施工方案"),
        )
    )
    return plan.calls[0]


def _transport(fake, **config):
    provider = OfficeCLIMCPTransportProvider(
        OfficeCLIMCPTransportConfig(EXECUTABLE, **config),
        stdio_factory=fake.stdio_factory,
        session_factory=fake.session_factory,
    )
    return provider.create()


def test_initialize_tools_list_and_contract_snapshot() -> None:
    fake = FakeSDK()
    transport = _transport(fake)
    transport.connect()
    try:
        assert transport.contract is not None
        assert transport.contract.server_name == "officecli"
        assert transport.contract.server_version == "1.0.143"
        assert transport.contract.protocol_version == "2024-11-05"
        assert transport.contract.tool_name == "officecli"
        assert fake.parameters[0].command == EXECUTABLE
        assert fake.parameters[0].args == ["mcp"]
    finally:
        transport.close()


def test_tools_call_uses_fixed_name_and_command_array() -> None:
    fake = FakeSDK()
    transport = _transport(fake)
    transport.connect()
    try:
        result = transport.call(_call())
        assert result.success is True
        assert fake.session.calls == [
            (
                "officecli",
                {
                    "command": [
                        "create",
                        "workspace/output/task-001/方案.docx",
                    ]
                },
            )
        ]
    finally:
        transport.close()


def test_schema_or_version_mismatch_fails_connection() -> None:
    fake = FakeSDK(
        FakeSession(initialize=initialize_result(version="1.0.999"))
    )
    transport = _transport(fake)
    with pytest.raises(OfficeCLIMCPContractError):
        transport.connect()
    assert fake.stdio_exited == 1


def test_timeout_is_stable_and_transport_closes() -> None:
    fake = FakeSDK(FakeSession(call_delay=0.1))
    transport = _transport(fake, call_timeout=0.01)
    transport.connect()
    with pytest.raises(OfficeCLIMCPTimeoutError):
        transport.call(_call())
    transport.close()
    transport.close()
    assert fake.session.exited == 1
    assert fake.stdio_exited == 1


def test_sdk_error_is_converted() -> None:
    fake = FakeSDK(FakeSession(call_error=RuntimeError("external secret")))
    transport = _transport(fake)
    transport.connect()
    try:
        with pytest.raises(OfficeCLIMCPCallError) as error:
            transport.call(_call())
        assert "external secret" not in str(error.value)
    finally:
        transport.close()


def test_tool_error_result_is_standardized() -> None:
    session = FakeSession(
        call_result=SimpleNamespace(
            isError=True,
            content=(SimpleNamespace(type="text", text="invalid value"),),
        )
    )
    fake = FakeSDK(session)
    transport = _transport(fake)
    transport.connect()
    try:
        result = transport.call(_call())
        assert result.success is False
        assert result.error_code == "SHF-OFFICE-MCP-TOOL_FAILED"
    finally:
        transport.close()


def test_transport_rejects_non_mapper_request() -> None:
    fake = FakeSDK()
    transport = _transport(fake)
    transport.connect()
    try:
        with pytest.raises(OfficeCLIMCPRequestError):
            transport.call({"command": ["raw", "secret.docx"]})
        assert fake.session.calls == []
    finally:
        transport.close()
