import pytest

from app.mcp_servers.office.runtime import OfficeCLIRequestError
from app.mcp_servers.office.runtime.mcp_bridge import OfficeCLIMCPBridgeAdapter

from .helpers import Provider, RecordingTransport, request


@pytest.mark.parametrize("arguments", [
    {"path": "C:/secret.docx"},
    {"content": {"command": "officecli create"}},
    {"shell": True},
    {"executable": "officecli"},
])
def test_paths_commands_and_shell_are_rejected_before_transport(arguments) -> None:
    transport = RecordingTransport()
    with pytest.raises(OfficeCLIRequestError):
        OfficeCLIMCPBridgeAdapter(Provider(transport)).create_document(
            request(arguments=arguments)
        )
    assert transport.calls == []


def test_bridge_has_no_dynamic_tool_argument() -> None:
    bridge = OfficeCLIMCPBridgeAdapter(Provider(RecordingTransport()))
    assert not hasattr(bridge, "call_tool")
    assert not hasattr(bridge, "discover_tools")
