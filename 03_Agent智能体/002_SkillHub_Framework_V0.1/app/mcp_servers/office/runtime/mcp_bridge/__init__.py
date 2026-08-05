"""OfficeCLI 外部MCP Server Bridge。"""

from .adapter import OfficeCLIMCPBridgeAdapter
from .errors import BridgeConnectionError, BridgeRequestError, BridgeResponseError, BridgeToolError, OfficeCLIMCPBridgeError
from .models import OfficeCLIBridgeTool, OfficeCLIMCPCall, OfficeCLIMCPResult
from .protocols import ExternalMCPTransportProtocol, OfficeCLIMCPBridgeProtocol, TransportProviderProtocol

__all__ = [
    "BridgeConnectionError", "BridgeRequestError", "BridgeResponseError",
    "BridgeToolError", "ExternalMCPTransportProtocol", "OfficeCLIBridgeTool",
    "OfficeCLIMCPBridgeAdapter", "OfficeCLIMCPBridgeError",
    "OfficeCLIMCPBridgeProtocol", "OfficeCLIMCPCall", "OfficeCLIMCPResult",
    "TransportProviderProtocol",
]
