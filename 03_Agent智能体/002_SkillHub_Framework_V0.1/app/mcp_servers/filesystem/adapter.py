"""固定FileSystem MCP Tool Adapter。"""

from typing import Any, Callable, Mapping
import zipfile

from app.mcp_servers.permissions import (
    DenyAllMCPServerPermissionPolicy,
    MCPServerPermissionPolicyProtocol,
)

from .models import FileSystemToolDefinition
from .tools import DeleteConfirmationError, FileSystemTools, UnsupportedFileTypeError


class FileSystemMCPServerAdapter:
    TOOL_DEFINITIONS = (
        FileSystemToolDefinition("filesystem.list", "列举任务目录文件", {"source": "string"}, {"files": "array"}, "FILE_LIST"),
        FileSystemToolDefinition("filesystem.read", "读取任务文件", {"source": "string"}, {"file": "object", "content": "bytes"}, "FILE_READ"),
        FileSystemToolDefinition("filesystem.write", "写入任务文件", {"target": "string", "content": "bytes"}, {"file": "object"}, "FILE_WRITE"),
        FileSystemToolDefinition("filesystem.copy", "复制任务文件", {"source": "string", "target": "string"}, {"file": "object"}, "FILE_COPY"),
        FileSystemToolDefinition("filesystem.move", "移动任务文件", {"source": "string", "target": "string"}, {"file": "object"}, "FILE_MOVE"),
        FileSystemToolDefinition("filesystem.rename", "重命名任务文件", {"source": "string", "target": "string"}, {"file": "object"}, "FILE_RENAME"),
        FileSystemToolDefinition("filesystem.archive", "创建或安全解压ZIP", {"archive_action": "string"}, {"file": "object", "files": "array"}, "FILE_ARCHIVE"),
        FileSystemToolDefinition("filesystem.request_delete", "请求删除确认", {"path": "string", "expected_version": "string", "expected_checksum": "string"}, {"confirmation_id": "string"}, "FILE_DELETE"),
        FileSystemToolDefinition("filesystem.confirm_delete", "确认删除文件", {"path": "string", "confirmation_id": "string"}, {"file": "object"}, "FILE_DELETE"),
    )
    ALLOWED_TOOLS = frozenset(item.name for item in TOOL_DEFINITIONS)

    def __init__(
        self,
        tools: FileSystemTools,
        permission_policy: MCPServerPermissionPolicyProtocol | None = None,
    ) -> None:
        self._tools = tools
        self._permission_policy = (
            permission_policy or DenyAllMCPServerPermissionPolicy()
        )

    def handle(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            if payload.get("method") != "tools/call":
                return self._error("SHF-SVC-FILE-INVALID_PATH", "只支持tools/call")
            params = self._mapping(payload.get("params"))
            tool_name = params.get("name")
            if tool_name not in self.ALLOWED_TOOLS:
                return self._error("SHF-MCP-TOOL-NOT_FOUND", "FileSystem Tool不存在")
            context = self._mapping(params.get("_meta"))
            for key in ("task_id", "trace_id", "span_id", "skill_id"):
                if not isinstance(context.get(key), str) or not context[key]:
                    raise ValueError(f"缺少Runtime Context：{key}")
            definition = next(
                item for item in self.TOOL_DEFINITIONS if item.name == tool_name
            )
            if not self._permission_policy.allows(
                str(context["skill_id"]), definition.permission
            ):
                raise PermissionError("Skill无权直接调用FileSystem MCP Tool")
            args = self._mapping(params.get("arguments", {}))
            task_id = str(context["task_id"])
            handlers: Mapping[str, Callable[[Mapping[str, Any], str], Mapping[str, Any]]] = {
                "filesystem.list": self._tools.list_files,
                "filesystem.read": self._tools.read_file,
                "filesystem.write": self._tools.write_file,
                "filesystem.copy": self._tools.copy_file,
                "filesystem.move": self._tools.move_file,
                "filesystem.rename": self._tools.rename_file,
                "filesystem.archive": self._tools.archive,
                "filesystem.request_delete": self._tools.request_delete,
                "filesystem.confirm_delete": self._tools.confirm_delete,
            }
            return {"content": handlers[str(tool_name)](args, task_id)}
        except FileNotFoundError:
            return self._error("SHF-SVC-FILE-NOT_FOUND", "文件不存在")
        except DeleteConfirmationError as exc:
            return self._error("SHF-SVC-FILE-DELETE_CONFIRM_REQUIRED", str(exc))
        except UnsupportedFileTypeError as exc:
            return self._error("SHF-SVC-FILE-UNSUPPORTED_TYPE", str(exc))
        except PermissionError as exc:
            return self._error("SHF-SVC-FILE-PERMISSION_DENIED", str(exc))
        except OverflowError:
            return self._error("SHF-SVC-FILE-TOO_LARGE", "文件大小超限")
        except (FileExistsError, IsADirectoryError, TypeError, ValueError, zipfile.BadZipFile) as exc:
            return self._error("SHF-SVC-FILE-INVALID_PATH", str(exc))

    @staticmethod
    def _mapping(value: Any) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise TypeError("MCP字段必须是对象")
        return value

    @staticmethod
    def _error(error_code: str, message: str) -> Mapping[str, Any]:
        return {"is_error": True, "error_code": error_code, "message": message}
