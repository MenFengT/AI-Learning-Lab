"""OfficeCLI官方SDK Transport稳定异常。"""


class OfficeCLIMCPTransportError(Exception):
    error_code = "SHF-OFFICE-MCP-FAILED"


class OfficeCLIMCPConnectionError(OfficeCLIMCPTransportError):
    error_code = "SHF-OFFICE-MCP-CONNECTION_FAILED"


class OfficeCLIMCPContractError(OfficeCLIMCPTransportError):
    error_code = "SHF-OFFICE-MCP-CONTRACT_INVALID"


class OfficeCLIMCPRequestError(OfficeCLIMCPTransportError):
    error_code = "SHF-OFFICE-MCP-REQUEST_INVALID"


class OfficeCLIMCPTimeoutError(OfficeCLIMCPTransportError):
    error_code = "SHF-OFFICE-MCP-TIMEOUT"


class OfficeCLIMCPCallError(OfficeCLIMCPTransportError):
    error_code = "SHF-OFFICE-MCP-CALL_FAILED"


class OfficeCLIMCPClosedError(OfficeCLIMCPTransportError):
    error_code = "SHF-OFFICE-MCP-CLOSED"
