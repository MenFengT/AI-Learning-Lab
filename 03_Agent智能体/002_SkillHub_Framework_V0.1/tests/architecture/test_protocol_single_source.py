import ast
import unittest
from pathlib import Path

from app.services import (
    AuditServiceProtocol as PublicAuditServiceProtocol,
)
from app.services import MCPClientProtocol as PublicMCPClientProtocol
from app.services.audit.protocols import AuditServiceProtocol
from app.services.mcp.protocols import MCPClientProtocol
from app.services.protocols import (
    AuditServiceProtocol as LegacyAuditServiceProtocol,
)
from app.services.protocols import MCPClientProtocol as LegacyMCPClientProtocol


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_ROOT = PROJECT_ROOT / "app" / "services"


class ProtocolSingleSourceTests(unittest.TestCase):
    def test_mcp_client_protocol_has_one_real_definition(self) -> None:
        definitions = self._find_class_definitions("MCPClientProtocol")

        self.assertEqual(
            definitions,
            (SERVICES_ROOT / "mcp" / "protocols.py",),
        )

    def test_audit_service_protocol_has_one_real_definition(self) -> None:
        definitions = self._find_class_definitions("AuditServiceProtocol")

        self.assertEqual(
            definitions,
            (SERVICES_ROOT / "audit" / "protocols.py",),
        )

    def test_legacy_and_public_mcp_imports_are_same_object(self) -> None:
        self.assertIs(LegacyMCPClientProtocol, MCPClientProtocol)
        self.assertIs(PublicMCPClientProtocol, MCPClientProtocol)

    def test_legacy_and_public_audit_imports_are_same_object(self) -> None:
        self.assertIs(LegacyAuditServiceProtocol, AuditServiceProtocol)
        self.assertIs(PublicAuditServiceProtocol, AuditServiceProtocol)

    @staticmethod
    def _find_class_definitions(class_name: str) -> tuple[Path, ...]:
        definitions: list[Path] = []
        for path in sorted(SERVICES_ROOT.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            if any(
                isinstance(node, ast.ClassDef) and node.name == class_name
                for node in ast.walk(tree)
            ):
                definitions.append(path)
        return tuple(definitions)


if __name__ == "__main__":
    unittest.main()
