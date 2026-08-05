"""Configuration Layer端口。"""

from pathlib import Path
from typing import Mapping, Protocol, runtime_checkable

from .models import ApplicationConfig


@runtime_checkable
class ConfigLoaderProtocol(Protocol):
    def load(
        self,
        dotenv_path: Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> ApplicationConfig: ...
