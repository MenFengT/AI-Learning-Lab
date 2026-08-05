import tempfile
import unittest
from pathlib import Path

from app.registry import ManifestValidationError, load_manifest, parse_manifest


VALID_MANIFEST = """
manifest_version: "0.1"
namespace: local
skill:
  name: material_plan
  version: "0.2.0"
  description: 生成材料计划
  lifecycle_status: ACTIVE
inputs:
  - name: task
    type: string
    required: true
    description: 用户任务
outputs:
  - name: result
    type: string
    required: true
    description: 处理结果
permissions:
  - FILE_READ
routing:
  keywords:
    - 材料计划
"""


class SkillManifestTests(unittest.TestCase):
    def test_load_valid_yaml_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "skill.yaml"
            path.write_text(VALID_MANIFEST, encoding="utf-8")

            registration = load_manifest(path)

        self.assertEqual(registration.skill_id, "local/material_plan@0.2.0")
        self.assertEqual(registration.manifest_version, "0.1")
        self.assertEqual(registration.metadata.inputs[0].name, "task")

    def test_manifest_rejects_import_path(self) -> None:
        manifest = {
            "manifest_version": "0.1",
            "skill": {
                "name": "material_plan",
                "version": "0.2.0",
                "description": "材料计划",
                "import_path": "app.skills.material.MaterialSkill",
            },
        }
        with self.assertRaisesRegex(ManifestValidationError, "禁止字段"):
            parse_manifest(manifest)

    def test_manifest_rejects_unknown_and_invalid_typed_fields(self) -> None:
        manifest = {
            "manifest_version": "0.1",
            "skill": {
                "name": "material_plan",
                "version": "0.2.0",
                "description": "材料计划",
            },
            "inputs": [
                {
                    "name": "task",
                    "type": "string",
                    "required": "yes",
                    "description": "任务",
                }
            ],
        }
        with self.assertRaisesRegex(ManifestValidationError, "布尔值"):
            parse_manifest(manifest)

    def test_safe_loader_rejects_python_yaml_tag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "skill.yaml"
            path.write_text(
                "!!python/object/apply:os.system ['echo unsafe']",
                encoding="utf-8",
            )
            with self.assertRaises(ManifestValidationError):
                load_manifest(path)


if __name__ == "__main__":
    unittest.main()
