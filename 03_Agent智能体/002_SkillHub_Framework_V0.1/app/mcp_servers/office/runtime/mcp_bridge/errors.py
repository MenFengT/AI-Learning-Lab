"""OfficeCLI MCP Bridge 稳定异常。"""


class OfficeCLIMCPBridgeError(Exception):
    error_code = "SHF-OFFICE-BRIDGE-FAILED"


class BridgeConnectionError(OfficeCLIMCPBridgeError):
    error_code = "SHF-OFFICE-BRIDGE-CONNECTION_FAILED"


class BridgeRequestError(OfficeCLIMCPBridgeError):
    error_code = "SHF-OFFICE-BRIDGE-REQUEST_INVALID"


class BridgeResponseError(OfficeCLIMCPBridgeError):
    error_code = "SHF-OFFICE-BRIDGE-RESPONSE_INVALID"


class BridgeToolError(OfficeCLIMCPBridgeError):
    def __init__(self, message: str, error_code: str = "SHF-OFFICE-BRIDGE-TOOL_FAILED") -> None:
        super().__init__(message)
        self.error_code = error_code
