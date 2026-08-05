"""Skill Registry公开接口。"""

from .exceptions import (
    ActiveVersionConflictError,
    DuplicateSkillError,
    ManifestValidationError,
    RegistryError,
    SkillNotFoundError,
)
from .health import check_registration_health
from .manifest import load_manifest, parse_manifest
from .models import (
    HealthCheckResult,
    HealthStatus,
    SchemaField,
    SkillLifecycleStatus,
    SkillMetadata,
    SkillRegistration,
    build_skill_id,
)
from .protocols import RegistryStore, SkillCatalog
from .registry import SkillRegistry
from .store import InMemoryRegistryStore

__all__ = [
    "ActiveVersionConflictError",
    "DuplicateSkillError",
    "HealthCheckResult",
    "HealthStatus",
    "InMemoryRegistryStore",
    "ManifestValidationError",
    "RegistryError",
    "RegistryStore",
    "SchemaField",
    "SkillCatalog",
    "SkillLifecycleStatus",
    "SkillMetadata",
    "SkillNotFoundError",
    "SkillRegistration",
    "SkillRegistry",
    "build_skill_id",
    "check_registration_health",
    "load_manifest",
    "parse_manifest",
]
