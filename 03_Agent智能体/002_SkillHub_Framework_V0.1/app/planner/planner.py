"""Planner编排纯数据计划生成和校验，不拥有执行权。"""

from datetime import datetime, timezone
from uuid import uuid4

from .errors import PlanGenerationError, PlanValidationError
from .models import TaskPlan, UserRequest
from .protocols import (
    PlanDraftProviderProtocol,
    PlanIdFactoryProtocol,
    PlannerClockProtocol,
)
from .validators import validate_task_plan


class UTCPlannerClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class UUIDPlanIdFactory:
    def create(self) -> str:
        return f"plan-{uuid4().hex}"


class Planner:
    """调用注入的草案Provider并产出已验证TaskPlan。"""

    def __init__(
        self,
        draft_provider: PlanDraftProviderProtocol,
        *,
        clock: PlannerClockProtocol | None = None,
        id_factory: PlanIdFactoryProtocol | None = None,
        max_steps: int = 100,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps必须大于0")
        self._draft_provider = draft_provider
        self._clock = clock or UTCPlannerClock()
        self._id_factory = id_factory or UUIDPlanIdFactory()
        self._max_steps = max_steps

    def create_plan(self, request: UserRequest) -> TaskPlan:
        if not isinstance(request, UserRequest):
            raise PlanGenerationError("request必须是UserRequest")
        try:
            steps = tuple(self._draft_provider.generate_steps(request))
        except Exception as exc:
            raise PlanGenerationError("计划草案生成失败") from exc
        plan = TaskPlan(
            plan_id=self._id_factory.create(),
            task_id=request.task_id,
            created_at=self._clock.now(),
            steps=steps,
            metadata={"planner_mode": "CONTRACT"},
        )
        try:
            validate_task_plan(plan, max_steps=self._max_steps)
        except PlanValidationError:
            raise
        return plan
