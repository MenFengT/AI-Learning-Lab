import tempfile
import unittest
from pathlib import Path

from app.mcp_servers.filesystem import (
    FileSystemTools,
    InMemoryFileIdentityStore,
    WorkspacePolicy,
)


class FileIdentityStoreTests(unittest.TestCase):
    def test_identity_survives_tool_instance_reconstruction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = InMemoryFileIdentityStore()
            first_tools = FileSystemTools(
                WorkspacePolicy(root),
                max_file_size=1024,
                identity_store=store,
            )
            first = first_tools.write_file(
                {"target": "processing/stable.txt", "content": b"v1"},
                "task-identity",
            )["file"]

            rebuilt_tools = FileSystemTools(
                WorkspacePolicy(root),
                max_file_size=1024,
                identity_store=store,
            )
            rebuilt = rebuilt_tools.read_file(
                {"source": "processing/stable.txt"},
                "task-identity",
            )["file"]
            updated = rebuilt_tools.write_file(
                {
                    "target": "processing/stable.txt",
                    "content": b"v2",
                    "overwrite": True,
                    "expected_version": rebuilt["version"],
                },
                "task-identity",
            )["file"]

        self.assertEqual(rebuilt["file_id"], first["file_id"])
        self.assertEqual(rebuilt["version"], first["version"])
        self.assertEqual(updated["file_id"], first["file_id"])
        self.assertEqual(updated["version"], "2")


if __name__ == "__main__":
    unittest.main()
