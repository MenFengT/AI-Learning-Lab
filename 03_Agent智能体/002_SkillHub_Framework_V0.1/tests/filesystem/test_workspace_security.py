import tempfile
import unittest
from pathlib import Path

from app.mcp_servers.filesystem import WorkspacePolicy as ServerWorkspacePolicy
from app.services.filesystem import WorkspacePolicy


class WorkspaceSecurityTests(unittest.TestCase):
    def test_valid_logical_path(self) -> None:
        self.assertEqual(
            WorkspacePolicy().validate_path("processing/folder/file.txt"),
            "processing/folder/file.txt",
        )

    def test_traversal_absolute_unc_and_uri_are_rejected(self) -> None:
        policy = WorkspacePolicy()
        attacks = (
            "processing/../secret.txt",
            "C:/secret.txt",
            "//server/share/file.txt",
            "file://workspace/input/file.txt",
            "/etc/passwd",
        )
        for path in attacks:
            with self.subTest(path=path), self.assertRaises(ValueError):
                policy.validate_path(path)

    def test_server_policy_binds_path_to_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            policy = ServerWorkspacePolicy(Path(directory))
            first = policy.resolve("processing/file.txt", "task-001", write=True)
            second = policy.resolve("processing/file.txt", "task-002", write=True)
            self.assertNotEqual(first, second)
            self.assertIn("task-001", str(first))
            self.assertIn("task-002", str(second))

    def test_server_policy_rejects_symlink_escape_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = ServerWorkspacePolicy(root)
            task_root = root / "processing" / "task-001"
            task_root.mkdir(parents=True)
            link = task_root / "escape"
            try:
                link.symlink_to(root.parent, target_is_directory=True)
            except OSError:
                self.skipTest("当前环境不允许创建符号链接")
            with self.assertRaisesRegex(ValueError, "超出"):
                policy.resolve("processing/escape/secret.txt", "task-001")


if __name__ == "__main__":
    unittest.main()
