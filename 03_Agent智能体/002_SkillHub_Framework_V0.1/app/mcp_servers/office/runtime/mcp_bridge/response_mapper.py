"""官方MCP SDK响应到Bridge稳定结果的转换。"""

from typing import Any, Mapping

from .models import OfficeCLIMCPResult
from .transport_errors import OfficeCLIMCPCallError


class OfficeCLIMCPResponseMapper:
    def map(self, result: Any) -> OfficeCLIMCPResult:
        is_error = bool(getattr(result, "isError", getattr(result, "is_error", False)))
        blocks = tuple(_content_block(item) for item in getattr(result, "content", ()))
        if not blocks:
            raise OfficeCLIMCPCallError("OfficeCLI MCP响应缺少content")
        text = "\n".join(
            str(block["text"])
            for block in blocks
            if block.get("type") == "text" and block.get("text") is not None
        )
        if is_error:
            return OfficeCLIMCPResult(
                success=False,
                content=None,
                error_code="SHF-OFFICE-MCP-TOOL_FAILED",
                message=text or "OfficeCLI Tool调用失败",
                metadata={"content_types": tuple(block["type"] for block in blocks)},
            )
        return OfficeCLIMCPResult(
            success=True,
            content={"text": text, "content_types": tuple(block["type"] for block in blocks)},
            message="OfficeCLI Tool调用成功",
        )


def _content_block(value: Any) -> Mapping[str, Any]:
    block_type = getattr(value, "type", None)
    if not isinstance(block_type, str) or not block_type:
        raise OfficeCLIMCPCallError("OfficeCLI ContentBlock类型无效")
    if block_type == "text":
        text = getattr(value, "text", None)
        if not isinstance(text, str):
            raise OfficeCLIMCPCallError("OfficeCLI文本响应无效")
        return {"type": "text", "text": text}
    return {"type": block_type}
