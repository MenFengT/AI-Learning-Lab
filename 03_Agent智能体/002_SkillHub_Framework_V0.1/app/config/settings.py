from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Framework V0.1 的集中配置。"""

    app_name: str = "SkillHub Framework"
    version: str = "0.1"
    knowledge_root: Path = PROJECT_ROOT / "data" / "knowledge"
