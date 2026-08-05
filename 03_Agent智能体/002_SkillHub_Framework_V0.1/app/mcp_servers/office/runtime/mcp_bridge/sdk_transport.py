"""使用官方MCP Python SDK管理OfficeCLI stdio会话。"""

import asyncio
from concurrent.futures import Future, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
import ntpath
from queue import Queue
from threading import Event, Thread
from typing import Any, Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .contract_validator import OfficeCLIContractValidator, OfficeCLIServerContract
from .mapping_models import ExternalOfficeCLICall
from .models import OfficeCLIMCPResult
from .response_mapper import OfficeCLIMCPResponseMapper
from .transport_errors import (
    OfficeCLIMCPCallError,
    OfficeCLIMCPClosedError,
    OfficeCLIMCPConnectionError,
    OfficeCLIMCPRequestError,
    OfficeCLIMCPTimeoutError,
    OfficeCLIMCPTransportError,
)


_STOP = object()
_ALLOWED_VERBS = frozenset({"create", "open", "batch", "add", "set", "remove", "save"})
_FORBIDDEN_VERBS = frozenset({"raw", "raw-set", "add-part"})


@dataclass(frozen=True)
class OfficeCLIMCPTransportConfig:
    executable_path: str
    expected_version: str = "1.0.143"
    expected_protocol_version: str = "2024-11-05"
    connect_timeout: float = 10.0
    call_timeout: float = 30.0

    def __post_init__(self) -> None:
        if not isinstance(self.executable_path, str) or not ntpath.isabs(
            self.executable_path
        ):
            raise OfficeCLIMCPRequestError("OfficeCLI必须使用绝对可执行文件路径")
        if not self.executable_path.casefold().endswith("officecli.exe"):
            raise OfficeCLIMCPRequestError("OfficeCLI可执行文件名称无效")
        if not self.expected_version.strip() or not self.expected_protocol_version.strip():
            raise OfficeCLIMCPRequestError("OfficeCLI契约版本不能为空")
        if self.connect_timeout <= 0 or self.call_timeout <= 0:
            raise OfficeCLIMCPRequestError("OfficeCLI timeout必须大于0")


@dataclass(frozen=True)
class _WorkItem:
    call: ExternalOfficeCLICall
    future: Future[OfficeCLIMCPResult]


class OfficeCLIMCPTransport:
    """同步Bridge端口背后的单会话异步SDK Transport。"""

    def __init__(
        self,
        config: OfficeCLIMCPTransportConfig,
        *,
        validator: OfficeCLIContractValidator | None = None,
        response_mapper: OfficeCLIMCPResponseMapper | None = None,
        stdio_factory: Callable[..., Any] = stdio_client,
        session_factory: Callable[..., Any] = ClientSession,
    ) -> None:
        self._config = config
        self._validator = validator or OfficeCLIContractValidator(
            expected_server_version=config.expected_version,
            expected_protocol_version=config.expected_protocol_version,
        )
        self._response_mapper = response_mapper or OfficeCLIMCPResponseMapper()
        self._stdio_factory = stdio_factory
        self._session_factory = session_factory
        self._queue: Queue[object] = Queue()
        self._ready = Event()
        self._thread: Thread | None = None
        self._startup_error: BaseException | None = None
        self._contract: OfficeCLIServerContract | None = None
        self._closed = False

    @property
    def contract(self) -> OfficeCLIServerContract | None:
        return self._contract

    def connect(self) -> None:
        if self._closed:
            raise OfficeCLIMCPClosedError("OfficeCLI Transport已关闭")
        if self._thread is not None:
            return
        self._thread = Thread(
            target=self._run_thread,
            name="officecli-mcp-transport",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(self._config.connect_timeout):
            self.close()
            raise OfficeCLIMCPTimeoutError("OfficeCLI MCP initialize超时")
        if self._startup_error is not None:
            error = self._startup_error
            self.close()
            if isinstance(error, OfficeCLIMCPTransportError):
                raise error
            raise OfficeCLIMCPConnectionError("OfficeCLI MCP连接失败") from error

    def call(self, request: ExternalOfficeCLICall) -> OfficeCLIMCPResult:
        if self._closed:
            raise OfficeCLIMCPClosedError("OfficeCLI Transport已关闭")
        if self._thread is None or self._contract is None:
            raise OfficeCLIMCPConnectionError("OfficeCLI Transport尚未连接")
        _validate_call(request)
        future: Future[OfficeCLIMCPResult] = Future()
        self._queue.put(_WorkItem(request, future))
        try:
            return future.result(self._config.call_timeout + 1.0)
        except FutureTimeoutError as exc:
            raise OfficeCLIMCPTimeoutError("OfficeCLI MCP Tool调用超时") from exc

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._thread is not None and self._thread.is_alive():
            self._queue.put(_STOP)
            self._thread.join(self._config.connect_timeout)
        self._thread = None

    def is_connected(self) -> bool:
        return (
            not self._closed
            and self._thread is not None
            and self._thread.is_alive()
            and self._contract is not None
        )

    def _run_thread(self) -> None:
        try:
            asyncio.run(self._run_session())
        except BaseException as exc:
            self._startup_error = exc
            self._ready.set()

    async def _run_session(self) -> None:
        parameters = StdioServerParameters(
            command=self._config.executable_path,
            args=["mcp"],
        )
        async with self._stdio_factory(parameters) as (read, write):
            async with self._session_factory(read, write) as session:
                initialize_result = await asyncio.wait_for(
                    session.initialize(), self._config.connect_timeout
                )
                tools_result = await asyncio.wait_for(
                    session.list_tools(), self._config.connect_timeout
                )
                self._contract = self._validator.validate(
                    initialize_result, tools_result
                )
                self._ready.set()
                while True:
                    item = await asyncio.to_thread(self._queue.get)
                    if item is _STOP:
                        return
                    if not isinstance(item, _WorkItem):
                        continue
                    await self._execute(session, item)

    async def _execute(self, session: Any, item: _WorkItem) -> None:
        try:
            command = list(item.call.arguments["command"])
            result = await asyncio.wait_for(
                session.call_tool(
                    "officecli",
                    arguments={"command": command},
                ),
                self._config.call_timeout,
            )
            item.future.set_result(self._response_mapper.map(result))
        except asyncio.TimeoutError:
            item.future.set_exception(
                OfficeCLIMCPTimeoutError("OfficeCLI MCP Tool调用超时")
            )
        except OfficeCLIMCPTransportError as exc:
            item.future.set_exception(exc)
        except Exception as exc:
            item.future.set_exception(
                OfficeCLIMCPCallError("OfficeCLI MCP Tool调用失败")
            )


def _validate_call(request: ExternalOfficeCLICall) -> None:
    if not isinstance(request, ExternalOfficeCLICall):
        raise OfficeCLIMCPRequestError("Transport只接受Mapper强类型输出")
    if request.tool_name != "officecli" or set(request.arguments) != {"command"}:
        raise OfficeCLIMCPRequestError("OfficeCLI Tool请求不符合固定Schema")
    command = request.arguments["command"]
    if not isinstance(command, tuple) or not command:
        raise OfficeCLIMCPRequestError("OfficeCLI command必须是argv元组")
    verb = command[0].casefold()
    if verb in _FORBIDDEN_VERBS or verb not in _ALLOWED_VERBS:
        raise OfficeCLIMCPRequestError("OfficeCLI command不在Transport白名单")
    if len(command) < 2 or not _is_controlled_workspace_path(command[1]):
        raise OfficeCLIMCPRequestError("OfficeCLI禁止任意路径")
    if any(token.casefold() in _FORBIDDEN_VERBS for token in command):
        raise OfficeCLIMCPRequestError("OfficeCLI请求包含禁止能力")


def _is_controlled_workspace_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    parts = normalized.split("/")
    if len(parts) != 4 or parts[0] != "workspace":
        return False
    if parts[1] not in {"processing", "output"}:
        return False
    if any(part in {"", ".", ".."} for part in parts):
        return False
    if ":" in value or value.startswith(("/", "\\", "file://")):
        return False
    return parts[-1].casefold().endswith((".docx", ".xlsx", ".pptx"))
