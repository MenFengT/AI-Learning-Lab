"""OfficeCLI能力映射白名单。"""

from dataclasses import dataclass, field
from typing import Mapping

from .errors import BridgeRequestError
from .mapping_models import ExternalOfficeCLICall, OfficeCapability


_DEFAULT_ALLOWED: Mapping[OfficeCapability, frozenset[str]] = {
    OfficeCapability.CREATE_DOCUMENT: frozenset(
        {"create", "batch", "add", "set", "save"}
    ),
    OfficeCapability.UPDATE_DOCUMENT: frozenset(
        {"open", "batch", "set", "add", "remove", "save"}
    ),
    OfficeCapability.CONVERT_DOCUMENT: frozenset(),
    OfficeCapability.EXPORT_DOCUMENT: frozenset(),
}
_FORBIDDEN = frozenset({"raw", "raw-set", "add-part"})


@dataclass(frozen=True)
class OfficeCLICapabilityPolicy:
    """只校验Mapper生成的固定argv，不接受用户定义白名单。"""

    allowed_commands: Mapping[OfficeCapability, frozenset[str]] = field(
        default_factory=lambda: _DEFAULT_ALLOWED
    )

    def validate(
        self,
        capability: OfficeCapability,
        call: ExternalOfficeCLICall,
    ) -> None:
        command = call.arguments["command"]
        verb = command[0].casefold()
        if verb in _FORBIDDEN:
            raise BridgeRequestError(f"OfficeCLI禁止命令：{verb}")
        allowed = self.allowed_commands.get(capability, frozenset())
        if verb not in allowed:
            raise BridgeRequestError(
                f"{capability.value}不允许OfficeCLI命令：{verb}"
            )
        if any(token.casefold() in _FORBIDDEN for token in command):
            raise BridgeRequestError("OfficeCLI调用包含禁止能力")
