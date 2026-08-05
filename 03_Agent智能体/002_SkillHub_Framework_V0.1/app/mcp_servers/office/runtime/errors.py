"""OfficeCLI Runtime Adapter 稳定异常。"""


class OfficeCLIAdapterError(Exception):
    error_code = "SHF-OFFICE-CLI-FAILED"


class OfficeCLIRequestError(OfficeCLIAdapterError):
    error_code = "SHF-OFFICE-CLI-REQUEST_INVALID"


class OfficeCLIInvocationError(OfficeCLIAdapterError):
    error_code = "SHF-OFFICE-CLI-INVOCATION_FAILED"


class OfficeCLIResponseError(OfficeCLIAdapterError):
    error_code = "SHF-OFFICE-CLI-RESPONSE_INVALID"
