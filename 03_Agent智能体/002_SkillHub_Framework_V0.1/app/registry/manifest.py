"""Skill Manifest的安全解析与强类型校验。"""

from pathlib import Path
from typing import Any, Mapping

import yaml

from .exceptions import ManifestValidationError
from .models import (
    HealthStatus,
    SchemaField,
    SkillLifecycleStatus,
    SkillMetadata,
    SkillRegistration,
    build_skill_id,
)


_TOP_LEVEL_KEYS = {
    "manifest_version",
    "namespace",
    "skill",
    "inputs",
    "outputs",
    "permissions",
    "routing",
}
_SKILL_KEYS = {"name", "version", "description", "lifecycle_status"}
_ROUTING_KEYS = {"keywords"}
_FIELD_KEYS = {"name", "type", "required", "description", "default"}
_FORBIDDEN_KEYS = {
    "import",
    "import_path",
    "module",
    "class",
    "class_path",
    "python",
    "python_path",
    "entrypoint",
}


def load_manifest(path: str | Path) -> SkillRegistration:
    """从UTF-8 YAML文件加载Descriptor，不执行其中任何内容。"""
    manifest_path = Path(path)
    try:
        with manifest_path.open("r", encoding="utf-8") as stream:
            raw = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as exc:
        raise ManifestValidationError(f"Manifest读取失败：{manifest_path}") from exc
    return parse_manifest(raw)


def parse_manifest(raw: Any) -> SkillRegistration:
    """将安全加载后的对象转换为强类型Registration。"""
    try:
        root = _require_mapping(raw, "manifest")
        _reject_forbidden_keys(root)
        _reject_unknown_keys(root, _TOP_LEVEL_KEYS, "manifest")
        skill = _require_mapping(_required(root, "skill"), "skill")
        routing = _require_mapping(root.get("routing", {}), "routing")
        _reject_unknown_keys(skill, _SKILL_KEYS, "skill")
        _reject_unknown_keys(routing, _ROUTING_KEYS, "routing")

        namespace = _require_string(root.get("namespace", "local"), "namespace")
        manifest_version = _require_string(
            _required(root, "manifest_version"), "manifest_version"
        )
        name = _require_string(_required(skill, "name"), "skill.name")
        version = _require_string(_required(skill, "version"), "skill.version")
        description = _require_string(
            _required(skill, "description"), "skill.description"
        )
        lifecycle = SkillLifecycleStatus(
            _require_string(
                skill.get("lifecycle_status", "ACTIVE"),
                "skill.lifecycle_status",
            )
        )
        inputs = _parse_fields(root.get("inputs", []), "inputs")
        outputs = _parse_fields(root.get("outputs", []), "outputs")
        permissions = frozenset(
            _string_list(root.get("permissions", []), "permissions")
        )
        keywords = tuple(_string_list(routing.get("keywords", []), "keywords"))
        metadata = SkillMetadata(
            name=name,
            version=version,
            description=description,
            inputs=inputs,
            outputs=outputs,
            permissions=permissions,
            keywords=keywords,
        )
        return SkillRegistration(
            skill_id=build_skill_id(namespace, name, version),
            namespace=namespace,
            name=name,
            version=version,
            manifest_version=manifest_version,
            metadata=metadata,
            lifecycle_status=lifecycle,
            health_status=HealthStatus.UNKNOWN,
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, ManifestValidationError):
            raise
        raise ManifestValidationError(str(exc)) from exc


def _parse_fields(value: Any, label: str) -> tuple[SchemaField, ...]:
    if not isinstance(value, list):
        raise ManifestValidationError(f"{label}必须是列表")
    fields = []
    for index, raw_field in enumerate(value):
        item = _require_mapping(raw_field, f"{label}[{index}]")
        _reject_unknown_keys(item, _FIELD_KEYS, f"{label}[{index}]")
        fields.append(
            SchemaField(
                name=_require_string(_required(item, "name"), "field.name"),
                type=_require_string(_required(item, "type"), "field.type"),
                required=_require_bool(
                    _required(item, "required"), "field.required"
                ),
                description=_require_string(
                    _required(item, "description"), "field.description"
                ),
                default=item.get("default"),
            )
        )
    return tuple(fields)


def _reject_forbidden_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in _FORBIDDEN_KEYS:
                raise ManifestValidationError(f"Manifest禁止字段：{key}")
            _reject_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_keys(child)


def _reject_unknown_keys(
    value: Mapping[str, Any], allowed: set[str], label: str
) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ManifestValidationError(f"{label}包含未知字段：{sorted(unknown)}")


def _required(value: Mapping[str, Any], key: str) -> Any:
    if key not in value:
        raise ManifestValidationError(f"缺少必填字段：{key}")
    return value[key]


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ManifestValidationError(f"{label}必须是对象")
    return value


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{label}必须是非空字符串")
    return value.strip()


def _require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ManifestValidationError(f"{label}必须是布尔值")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ManifestValidationError(f"{label}必须是列表")
    return [_require_string(item, label) for item in value]
