"""创建并管理一次 SkillHub 任务的统一运行环境。"""

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol
from uuid import uuid4

from .execution_context import ExecutionContext
from .invocation_context import InvocationContext
from .lifecycle import Lifecycle, LifecycleStatus
from .trace import Trace


class RuntimeExtension(Protocol):
    """生命周期扩展接口，可用于 Audit、Service 或异步任务适配。"""

    def on_status_change(
        self,
        context: ExecutionContext,
        previous_status: LifecycleStatus,
        current_status: LifecycleStatus,
    ) -> None:
        """接收状态变化事件，不负责改变 Runtime 状态。"""
        ...


class ExtensionLevel(str, Enum):
    """扩展异常对主任务的影响级别。"""

    BLOCKING = "BLOCKING"
    NON_BLOCKING = "NON_BLOCKING"


@dataclass(frozen=True)
class RegisteredExtension:
    """扩展及其执行策略的注册记录。"""

    extension: RuntimeExtension
    level: ExtensionLevel


@dataclass
class RuntimeEnvironment:
    """聚合一次任务的上下文、链路与生命周期。"""

    context: ExecutionContext
    trace: Trace
    lifecycle: Lifecycle


class RuntimeManager:
    """负责 Runtime 环境创建、查询和生命周期管理。"""

    def __init__(self) -> None:
        self._environments: dict[str, RuntimeEnvironment] = {}
        self._extensions: list[RegisteredExtension] = []

    def register_extension(
        self,
        extension: RuntimeExtension,
        level: ExtensionLevel = ExtensionLevel.BLOCKING,
    ) -> None:
        """注册生命周期观察扩展，不允许扩展接管状态迁移。"""
        self._extensions.append(RegisteredExtension(extension, level))

    def create_environment(
        self,
        user_request: str,
        *,
        user_id: str | None = None,
        inputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeEnvironment:
        request = user_request.strip()
        if not request:
            raise ValueError("用户请求不能为空")

        trace = Trace.create()
        context = ExecutionContext(
            task_id=uuid4().hex,
            trace_id=trace.trace_id,
            user_id=user_id,
            user_request=request,
            inputs=inputs or {},
            metadata=metadata or {},
        )
        environment = RuntimeEnvironment(
            context=context,
            trace=trace,
            lifecycle=Lifecycle(),
        )
        self._environments[context.task_id] = environment
        return environment

    def get_environment(self, task_id: str) -> RuntimeEnvironment:
        try:
            return self._environments[task_id]
        except KeyError as exc:
            raise KeyError(f"任务运行环境不存在：{task_id}") from exc

    def create_invocation_context(
        self, task_id: str, skill_id: str
    ) -> InvocationContext:
        """为已路由的 Skill 创建同一 trace 下的独立执行 span。"""
        environment = self.get_environment(task_id)
        if environment.lifecycle.status not in {
            LifecycleStatus.PLANNING,
            LifecycleStatus.EXECUTING,
        }:
            raise ValueError("只有PLANNING状态可以创建Skill调用上下文")
        child_trace = environment.trace.create_child()
        return InvocationContext(
            task_id=environment.context.task_id,
            trace_id=child_trace.trace_id,
            span_id=child_trace.span_id,
            skill_id=skill_id,
            user_id=environment.context.user_id,
            metadata=environment.context.metadata,
        )

    def transition(self, task_id: str, next_status: LifecycleStatus) -> None:
        environment = self.get_environment(task_id)
        previous_status = environment.lifecycle.status
        environment.lifecycle.transition_to(next_status)
        self._notify_extensions(environment.context, previous_status, next_status)

    def complete(self, task_id: str, outputs: dict[str, Any] | None = None) -> None:
        environment = self.get_environment(task_id)
        if environment.lifecycle.status is not LifecycleStatus.EXECUTING:
            raise ValueError("只有 EXECUTING 状态的任务可以完成")
        environment.context.outputs.update(deepcopy(outputs or {}))
        self.transition(task_id, LifecycleStatus.COMPLETED)

    def fail(self, task_id: str, error: str) -> None:
        environment = self.get_environment(task_id)
        if environment.lifecycle.status in {
            LifecycleStatus.COMPLETED,
            LifecycleStatus.FAILED,
        }:
            raise ValueError("终态任务不能再次失败")
        environment.context.metadata["error"] = error
        self.transition(task_id, LifecycleStatus.FAILED)

    def _notify_extensions(
        self,
        context: ExecutionContext,
        previous_status: LifecycleStatus,
        current_status: LifecycleStatus,
    ) -> None:
        for registration in tuple(self._extensions):
            try:
                registration.extension.on_status_change(
                    context, previous_status, current_status
                )
            except Exception as exc:
                if registration.level is ExtensionLevel.BLOCKING:
                    raise
                context.metadata.setdefault("extension_errors", []).append(
                    {
                        "extension_name": type(registration.extension).__name__,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "previous_status": previous_status.value,
                        "current_status": current_status.value,
                    }
                )
