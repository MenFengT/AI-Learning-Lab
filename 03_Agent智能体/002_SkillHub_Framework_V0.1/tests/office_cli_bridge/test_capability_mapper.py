import inspect

import pytest

from app.mcp_servers.office.runtime.mcp_bridge.capability_mapper import (
    OfficeCLICapabilityMapper,
)
from app.mcp_servers.office.runtime.mcp_bridge.capability_policy import (
    OfficeCLICapabilityPolicy,
)
from app.mcp_servers.office.runtime.mcp_bridge.errors import BridgeRequestError
from app.mcp_servers.office.runtime.mcp_bridge.mapping_models import (
    ExternalOfficeCLICall,
    OfficeCapability,
    OfficeCapabilityRequest,
    OfficeDocumentContent,
)


def _request(capability=OfficeCapability.CREATE_DOCUMENT, name="方案.docx"):
    return OfficeCapabilityRequest(
        capability=capability,
        task_id="task-001",
        document_name=name,
        content=OfficeDocumentContent("地下室防水施工方案", ("工程概况",)),
    )


def test_create_document_generates_controlled_command_arrays() -> None:
    plan = OfficeCLICapabilityMapper(OfficeCLICapabilityPolicy()).map(
        _request()
    )

    commands = tuple(call.arguments["command"] for call in plan.calls)
    assert tuple(command[0] for command in commands) == (
        "create",
        "batch",
        "save",
    )
    assert commands[0] == (
        "create",
        "workspace/output/task-001/方案.docx",
    )
    assert all(call.tool_name == "officecli" for call in plan.calls)


def test_update_document_generates_controlled_command_arrays() -> None:
    plan = OfficeCLICapabilityMapper(OfficeCLICapabilityPolicy()).map(
        _request(OfficeCapability.UPDATE_DOCUMENT)
    )

    commands = tuple(call.arguments["command"] for call in plan.calls)
    assert tuple(command[0] for command in commands) == (
        "open",
        "batch",
        "save",
    )
    assert '"command":"set"' in commands[1][3]


@pytest.mark.parametrize("verb", ("raw", "raw-set", "add-part"))
def test_policy_rejects_raw_capabilities(verb) -> None:
    call = ExternalOfficeCLICall("officecli", {"command": (verb, "file.docx")})
    with pytest.raises(BridgeRequestError):
        OfficeCLICapabilityPolicy().validate(
            OfficeCapability.CREATE_DOCUMENT,
            call,
        )


def test_request_has_no_user_command_injection_surface() -> None:
    assert "command" not in inspect.signature(OfficeCapabilityRequest).parameters
    with pytest.raises(TypeError):
        OfficeCapabilityRequest(
            capability=OfficeCapability.CREATE_DOCUMENT,
            task_id="task-001",
            document_name="safe.docx",
            content=OfficeDocumentContent("标题"),
            command="raw safe.docx document",
        )


@pytest.mark.parametrize(
    "name",
    ("../secret.docx", "folder/secret.docx", "C:\\secret.docx", "..docx"),
)
def test_path_traversal_and_paths_are_rejected(name) -> None:
    with pytest.raises(BridgeRequestError):
        _request(name=name)


def test_output_schema_is_stable_and_immutable() -> None:
    plan = OfficeCLICapabilityMapper(OfficeCLICapabilityPolicy()).map(
        _request()
    )
    call = plan.calls[0]

    assert call.tool_name == "officecli"
    assert set(call.arguments) == {"command"}
    assert isinstance(call.arguments["command"], tuple)
    with pytest.raises(TypeError):
        call.arguments["command"] = ("raw",)


@pytest.mark.parametrize(
    "capability",
    (OfficeCapability.CONVERT_DOCUMENT, OfficeCapability.EXPORT_DOCUMENT),
)
def test_unverified_capabilities_fail_closed(capability) -> None:
    with pytest.raises(BridgeRequestError):
        OfficeCLICapabilityMapper(OfficeCLICapabilityPolicy()).map(
            _request(capability)
        )
