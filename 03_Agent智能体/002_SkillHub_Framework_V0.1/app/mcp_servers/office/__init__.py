"""Office MCP Server固定适配器。"""

from .adapter import OfficeMCPServerAdapter
from .models import OfficeCLIAdapterProtocol, OfficeToolDefinition
from .tools import OFFICE_ALLOWED_TOOLS, OFFICE_TOOL_DEFINITIONS

__all__ = [
    "OFFICE_ALLOWED_TOOLS",
    "OFFICE_TOOL_DEFINITIONS",
    "OfficeCLIAdapterProtocol",
    "OfficeMCPServerAdapter",
    "OfficeToolDefinition",
]
