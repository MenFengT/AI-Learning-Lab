"""真实OfficeCLI Runtime的Composition Root装配。"""

from pathlib import Path

from app.config.models import ApplicationConfig
from app.mcp_servers.office.runtime.mcp_bridge.capability_mapper import (
    OfficeCLICapabilityMapper,
)
from app.mcp_servers.office.runtime.mcp_bridge.capability_policy import (
    OfficeCLICapabilityPolicy,
)
from app.mcp_servers.office.runtime.mcp_bridge.mapped_runtime import (
    MappedOfficeCLIRuntime,
)
from app.mcp_servers.office.runtime.mcp_bridge.sdk_provider import (
    OfficeCLIMCPTransportProvider,
)
from app.mcp_servers.office.runtime.mcp_bridge.sdk_transport import (
    OfficeCLIMCPTransportConfig,
)
from .officecli_output import LocalOfficeCLIOutputResolver


def create_real_officecli_runtime(
    application_config: ApplicationConfig,
    application_root: Path,
) -> MappedOfficeCLIRuntime:
    """仅依据显式配置装配真实Runtime，不读取环境变量。"""

    transport_provider = OfficeCLIMCPTransportProvider(
        OfficeCLIMCPTransportConfig(
            executable_path=application_config.office.executable_path,
            expected_version=application_config.office.version,
            expected_protocol_version="2024-11-05",
        )
    )
    return MappedOfficeCLIRuntime(
        OfficeCLICapabilityMapper(OfficeCLICapabilityPolicy()),
        transport_provider,
        LocalOfficeCLIOutputResolver(application_root),
    )
