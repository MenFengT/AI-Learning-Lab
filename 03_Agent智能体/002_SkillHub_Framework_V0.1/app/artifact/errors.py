"""Artifact Layer 错误定义。"""


class ArtifactError(RuntimeError):
    """Artifact Layer 基础错误。"""


class ArtifactNotFoundError(ArtifactError):
    """指定产物或产物版本不存在。"""


class ArtifactConflictError(ArtifactError):
    """产物版本或文件引用发生冲突。"""


class ArtifactStateError(ArtifactError):
    """产物状态转换不合法。"""


class ArtifactPermissionError(ArtifactError):
    """运行时上下文无权访问指定任务产物。"""
