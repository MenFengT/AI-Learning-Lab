"""OfficeCLI受控工作区输出解析端口。"""

from typing import Protocol, runtime_checkable

from app.services.filesystem.models import FileReference

from .models import OfficeCLIRequest


@runtime_checkable
class OfficeCLIOutputResolverProtocol(Protocol):
    """由Composition Root注入的受控输出解析端口。"""

    def prepare(self, request: OfficeCLIRequest) -> None: ...

    def resolve(self, request: OfficeCLIRequest) -> FileReference: ...
