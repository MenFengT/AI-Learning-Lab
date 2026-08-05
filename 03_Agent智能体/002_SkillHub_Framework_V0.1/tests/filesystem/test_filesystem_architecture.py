import ast
import unittest
from pathlib import Path

from app.mcp_servers.filesystem import FileSystemMCPServerAdapter
from app.services.filesystem import SecurityScannerProtocol, SecurityScanResult, SecurityScanStatus
from app.services.governance import Idempotency, OperationType

from .helpers import filesystem_policies


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class FileSystemArchitectureTests(unittest.TestCase):
    def test_fixed_tool_definitions_are_complete(self) -> None:
        expected = {"filesystem.list", "filesystem.read", "filesystem.write", "filesystem.copy", "filesystem.move", "filesystem.rename", "filesystem.archive", "filesystem.request_delete", "filesystem.confirm_delete"}
        self.assertEqual(FileSystemMCPServerAdapter.ALLOWED_TOOLS, expected)
        for definition in FileSystemMCPServerAdapter.TOOL_DEFINITIONS:
            self.assertTrue(definition.description)
            self.assertTrue(definition.input_schema)
            self.assertTrue(definition.output_schema)
            self.assertTrue(definition.permission)

    def test_service_has_no_direct_filesystem_or_shell_access(self) -> None:
        path = PROJECT_ROOT / "app" / "services" / "filesystem" / "service.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        forbidden = ("pathlib", "os", "shutil", "subprocess")
        self.assertFalse(any(name.startswith(forbidden) for name in imports))
        source = path.read_text(encoding="utf-8")
        self.assertNotIn("open(", source)

    def test_service_depends_on_governance_not_mcp_client(self) -> None:
        path = PROJECT_ROOT / "app" / "services" / "filesystem" / "service.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        self.assertNotIn("MCPClientProtocol", source)
        self.assertNotIn("_mcp_client", source)
        self.assertFalse(
            any(name.startswith("app.services.mcp") for name in imports)
        )
        self.assertIn("ServiceCallExecutorProtocol", source)
        self.assertIn("_governance_executor.execute", source)

    def test_all_operations_have_required_governance_policy(self) -> None:
        policies = filesystem_policies()
        expected = {
            "list": (OperationType.READ, Idempotency.IDEMPOTENT),
            "read": (OperationType.READ, Idempotency.IDEMPOTENT),
            "write": (
                OperationType.WRITE,
                Idempotency.IDEMPOTENT_WITH_KEY,
            ),
            "copy": (
                OperationType.WRITE,
                Idempotency.IDEMPOTENT_WITH_KEY,
            ),
            "move": (OperationType.MOVE, Idempotency.NON_IDEMPOTENT),
            "rename": (OperationType.MOVE, Idempotency.NON_IDEMPOTENT),
            "archive": (
                OperationType.ARCHIVE,
                Idempotency.IDEMPOTENT_WITH_KEY,
            ),
            "request_delete": (
                OperationType.DELETE,
                Idempotency.NON_IDEMPOTENT,
            ),
            "confirm_delete": (
                OperationType.DELETE,
                Idempotency.NON_IDEMPOTENT,
            ),
        }

        self.assertEqual(set(policies), set(expected))
        for operation, (operation_type, idempotency) in expected.items():
            with self.subTest(operation=operation):
                policy = policies[operation]
                self.assertEqual(policy.operation_type, operation_type)
                self.assertEqual(policy.idempotency, idempotency)
                if idempotency is Idempotency.NON_IDEMPOTENT:
                    self.assertEqual(policy.retry_policy.max_attempts, 1)

    def test_security_scanner_is_protocol_only(self) -> None:
        class Scanner:
            def scan(self, file_id: str, version: str, checksum: str) -> SecurityScanResult:
                return SecurityScanResult(SecurityScanStatus.NOT_SCANNED, file_id, version, checksum)
        self.assertIsInstance(Scanner(), SecurityScannerProtocol)


if __name__ == "__main__":
    unittest.main()
