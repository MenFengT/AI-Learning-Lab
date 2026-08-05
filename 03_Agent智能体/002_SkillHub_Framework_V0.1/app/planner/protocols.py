"""Planner纯数据生成协议。"""

from datetime import datetime
from typing import Protocol, runtime_checkable

from .models import PlanStep, TaskPlan, UserRequest


@runtime_checkable
class PlannerProtocol(Protocol):
    """只生成TaskPlan，不执行Step。"""

    def create_plan(self, request: UserRequest) -> TaskPlan: ...


@runtime_checkable
class PlanDraftProviderProtocol(Protocol):
    """提供纯数据Step草案，可由确定性策略或未来LLM适配器实现。"""

    def generate_steps(self, request: UserRequest) -> tuple[PlanStep, ...]: ...


class PlannerClockProtocol(Protocol):
    def now(self) -> datetime: ...


class PlanIdFactoryProtocol(Protocol):
    def create(self) -> str: ...
