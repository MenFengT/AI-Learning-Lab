from app.mcp_servers.office.runtime import OfficeCLIRuntimeProtocol
from app.mcp_servers.office.runtime.mcp_bridge import (
    OfficeCLIBridgeTool,
    OfficeCLIMCPBridgeAdapter,
    OfficeCLIMCPBridgeProtocol,
    TransportProviderProtocol,
)

from .helpers import Provider, RecordingTransport, request


def test_bridge_satisfies_runtime_and_bridge_protocols() -> None:
    provider = Provider(RecordingTransport())
    bridge = OfficeCLIMCPBridgeAdapter(provider)
    assert isinstance(provider, TransportProviderProtocol)
    assert isinstance(bridge, OfficeCLIMCPBridgeProtocol)
    assert isinstance(bridge, OfficeCLIRuntimeProtocol)


def test_fixed_tool_call_and_file_reference_conversion() -> None:
    transport = RecordingTransport()
    result = OfficeCLIMCPBridgeAdapter(Provider(transport)).create_document(request())
    assert transport.connect_count == 1
    assert transport.close_count == 1
    assert transport.calls[0].tool is OfficeCLIBridgeTool.CREATE_DOCUMENT
    assert transport.calls[0].task_id == "task-001"
    assert result.file_reference.file_id == "file-office-001"
    assert result.format == "docx"


def test_all_four_operations_use_fixed_tools() -> None:
    expected = {
        "create_document": OfficeCLIBridgeTool.CREATE_DOCUMENT,
        "update_document": OfficeCLIBridgeTool.UPDATE_DOCUMENT,
        "convert_document": OfficeCLIBridgeTool.CONVERT_DOCUMENT,
        "export_document": OfficeCLIBridgeTool.EXPORT_DOCUMENT,
    }
    for operation, tool in expected.items():
        transport = RecordingTransport()
        bridge = OfficeCLIMCPBridgeAdapter(Provider(transport))
        getattr(bridge, operation)(request(operation))
        assert transport.calls[0].tool is tool
