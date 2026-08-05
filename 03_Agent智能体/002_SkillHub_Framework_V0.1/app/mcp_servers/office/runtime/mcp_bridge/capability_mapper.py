"""固定SkillHub Office能力到OfficeCLI 1.0.143 MCP参数的安全映射。"""

import json

from .capability_policy import OfficeCLICapabilityPolicy
from .errors import BridgeRequestError
from .mapping_models import (
    ExternalOfficeCLICall,
    OfficeCapability,
    OfficeCapabilityPlan,
    OfficeCapabilityRequest,
)


class OfficeCLICapabilityMapper:
    """只生成受控argv；不执行Tool、不读文件、不处理业务。"""

    def __init__(self, policy: OfficeCLICapabilityPolicy) -> None:
        if not isinstance(policy, OfficeCLICapabilityPolicy):
            raise TypeError("policy必须是OfficeCLICapabilityPolicy")
        self._policy = policy

    def map(self, request: OfficeCapabilityRequest) -> OfficeCapabilityPlan:
        if not isinstance(request, OfficeCapabilityRequest):
            raise BridgeRequestError("Mapper只接受OfficeCapabilityRequest")
        if request.capability is OfficeCapability.CREATE_DOCUMENT:
            calls = self._create_document(request)
        elif request.capability is OfficeCapability.UPDATE_DOCUMENT:
            calls = self._update_document(request)
        else:
            raise BridgeRequestError(
                f"{request.capability.value}尚未通过真实OfficeCLI契约验证"
            )
        for call in calls:
            self._policy.validate(request.capability, call)
        return OfficeCapabilityPlan(request.capability, calls)

    @staticmethod
    def _create_document(
        request: OfficeCapabilityRequest,
    ) -> tuple[ExternalOfficeCLICall, ...]:
        document = _workspace_document(request)
        return (
            _call("create", document),
            _batch_call(document, request, update=False),
            _call("save", document),
        )

    @staticmethod
    def _update_document(
        request: OfficeCapabilityRequest,
    ) -> tuple[ExternalOfficeCLICall, ...]:
        document = _workspace_document(request)
        return (
            _call("open", document),
            _batch_call(document, request, update=True),
            _call("save", document),
        )


def _workspace_document(request: OfficeCapabilityRequest) -> str:
    return f"workspace/output/{request.task_id}/{request.document_name}"


def _batch_call(
    document: str,
    request: OfficeCapabilityRequest,
    *,
    update: bool,
) -> ExternalOfficeCLICall:
    content = request.content
    commands: list[dict[str, object]] = []
    if update:
        commands.append(
            {
                "command": "set",
                "path": "/body/p[1]",
                "props": {"text": content.title, "style": "Title"},
            }
        )
    else:
        commands.append(
            {
                "command": "add",
                "parent": "/body",
                "type": "paragraph",
                "props": {"text": content.title, "style": "Title"},
            }
        )
    commands.extend(
        {
            "command": "add",
            "parent": "/body",
            "type": "paragraph",
            "props": {"text": paragraph},
        }
        for paragraph in content.paragraphs
    )
    encoded = json.dumps(commands, ensure_ascii=False, separators=(",", ":"))
    return _call(
        "batch",
        document,
        "--commands",
        encoded,
        "--stop-on-error",
        "--json",
    )


def _call(*command: str) -> ExternalOfficeCLICall:
    return ExternalOfficeCLICall("officecli", {"command": tuple(command)})
