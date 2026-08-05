"""Office Service公共接口。"""

from .models import OfficeDocumentRequest, OfficeDocumentResult
from .protocols import OfficeServiceProtocol
from .service import OfficeService

__all__ = [
    "OfficeDocumentRequest",
    "OfficeDocumentResult",
    "OfficeService",
    "OfficeServiceProtocol",
]
