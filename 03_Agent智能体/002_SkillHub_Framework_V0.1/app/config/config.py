"""供Composition Root调用的统一配置入口。"""

from pathlib import Path
from typing import Mapping

from .loader import ConfigLoader
from .models import ApplicationConfig
from .protocols import ConfigLoaderProtocol


def load_application_config(
    dotenv_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
    *,
    loader: ConfigLoaderProtocol | None = None,
) -> ApplicationConfig:
    """显式构建配置，不缓存、不创建全局单例。"""
    selected_loader = loader or ConfigLoader()
    return selected_loader.load(dotenv_path, environ)
