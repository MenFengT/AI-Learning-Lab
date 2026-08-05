"""FileSystem MCP Tool描述与删除状态。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True)
class FileSystemToolDefinition:
    name: str
    description: str
    input_schema: Mapping[str, Any]
    output_schema: Mapping[str, Any]
    permission: str


@dataclass(frozen=True)
class PendingDelete:
    confirmation_id: str
    task_id: str
    logical_path: str
    file_id: str
    version: str
    checksum: str
    expire_time: datetime
