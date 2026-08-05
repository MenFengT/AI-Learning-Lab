"""OfficeCLI 安全 Runtime Adapter。"""

from .adapter import OfficeCLIAdapter
from .errors import OfficeCLIAdapterError, OfficeCLIInvocationError, OfficeCLIRequestError, OfficeCLIResponseError
from .models import OfficeCLIRequest, OfficeCLIResult
from .protocols import OfficeCLIRuntimeProtocol

__all__ = [
    "OfficeCLIAdapter",
    "OfficeCLIAdapterError",
    "OfficeCLIInvocationError",
    "OfficeCLIRequest",
    "OfficeCLIRequestError",
    "OfficeCLIResponseError",
    "OfficeCLIResult",
    "OfficeCLIRuntimeProtocol",
]
