"""Office MCP Server固定Tool目录。"""

from .models import OfficeToolDefinition


OFFICE_TOOL_DEFINITIONS = (
    OfficeToolDefinition(
        "office.create_document",
        "创建Word、Excel或PPT文档",
        {"output_name": "string", "content": "object"},
        {"file": "object", "format": "string"},
        "OFFICE_DOCUMENT_CREATE",
    ),
    OfficeToolDefinition(
        "office.update_document",
        "更新已有Word、Excel或PPT文档",
        {"source_file_id": "string", "source_version": "string"},
        {"file": "object", "format": "string"},
        "OFFICE_DOCUMENT_UPDATE",
    ),
    OfficeToolDefinition(
        "office.convert_document",
        "转换Office文档格式",
        {"source_file_id": "string", "target_format": "string"},
        {"file": "object", "format": "string"},
        "OFFICE_DOCUMENT_CONVERT",
    ),
    OfficeToolDefinition(
        "office.export_document",
        "导出Office文档",
        {"source_file_id": "string", "target_format": "string"},
        {"file": "object", "format": "string"},
        "OFFICE_DOCUMENT_EXPORT",
    ),
)

OFFICE_ALLOWED_TOOLS = frozenset(item.name for item in OFFICE_TOOL_DEFINITIONS)
