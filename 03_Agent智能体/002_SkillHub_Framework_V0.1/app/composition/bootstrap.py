"""应用启动装配入口；不启动网络、不执行任务。"""

from app.config.models import ApplicationConfig

from .container import ApplicationContainer
from .factory import ApplicationDependencies, ApplicationFactory


def bootstrap(
    dependencies: ApplicationDependencies,
    application_config: ApplicationConfig | None = None,
) -> ApplicationContainer:
    """使用显式配置创建独立对象图；不在此读取环境变量。"""

    return ApplicationFactory().create(dependencies, application_config)
