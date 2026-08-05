"""TaskPlan 执行适配层错误。"""


class ExecutionAdapterError(RuntimeError):
    """执行适配层基础错误。"""


class ExecutionStateError(ExecutionAdapterError):
    """Runtime 或计划状态不允许执行。"""


class StepExecutionError(ExecutionAdapterError):
    """单个计划步骤执行失败。"""

    def __init__(self, step_id: str, skill_id: str, message: str) -> None:
        super().__init__(message)
        self.step_id = step_id
        self.skill_id = skill_id
