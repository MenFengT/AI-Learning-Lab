"""Planner Contract Layer稳定异常。"""


class PlannerError(Exception):
    """Planner层异常基类。"""


class PlanGenerationError(PlannerError):
    """计划草案生成失败。"""


class PlanValidationError(PlannerError, ValueError):
    """TaskPlan不满足不可变契约或依赖规则。"""
