from pathlib import Path

import pytest

from app.mcp_servers.office.runtime.mcp_bridge.sdk_provider import (
    OfficeCLIMCPTransportProvider,
)
from app.mcp_servers.office.runtime.mcp_bridge.sdk_transport import (
    OfficeCLIMCPTransportConfig,
)


OFFICECLI = Path("C:/Users/MF/AppData/Local/OfficeCLI/officecli.exe")


@pytest.mark.skipif(not OFFICECLI.exists(), reason="OfficeCLI 1.0.143未安装")
def test_real_officecli_initialize_and_tools_list() -> None:
    transport = OfficeCLIMCPTransportProvider(
        OfficeCLIMCPTransportConfig(str(OFFICECLI), connect_timeout=15.0)
    ).create()
    transport.connect()
    try:
        assert transport.contract is not None
        assert transport.contract.server_name == "officecli"
        assert transport.contract.server_version == "1.0.143"
        assert transport.contract.protocol_version == "2024-11-05"
        assert transport.contract.tool_name == "officecli"
        assert set(transport.contract.input_schema["properties"]) == {
            "command"
        }
    finally:
        transport.close()
    assert transport.is_connected() is False
