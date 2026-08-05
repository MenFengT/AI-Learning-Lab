import ast
import unittest
from pathlib import Path

from app.mcp_registry import (
    DescriptorValidationError,
    InMemoryMCPServerStore,
)

from .helpers import descriptor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = PROJECT_ROOT / "app" / "mcp_registry"


class MCPRegistryArchitectureTests(unittest.TestCase):
    def test_registry_has_no_business_or_runtime_dependencies(self) -> None:
        forbidden_prefixes = (
            "app.skills",
            "app.registry",
            "app.services.knowledge",
            "app.services.filesystem",
            "app.runtime",
            "app.mcp_servers",
            "subprocess",
            "socket",
        )
        for path in REGISTRY_ROOT.glob("*.py"):
            tree = ast.parse(
                path.read_text(encoding="utf-8"), filename=str(path)
            )
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            violations = tuple(
                name
                for name in imports
                if name.startswith(forbidden_prefixes)
            )
            self.assertEqual(violations, (), f"{path.name}: {violations}")

    def test_registry_does_not_connect_or_execute_tools(self) -> None:
        forbidden_calls = {
            "connect",
            "send",
            "call",
            "execute",
            "open",
            "run",
            "popen",
        }
        for path in REGISTRY_ROOT.glob("*.py"):
            tree = ast.parse(
                path.read_text(encoding="utf-8"), filename=str(path)
            )
            calls = {
                node.func.attr.casefold()
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
            }
            self.assertEqual(
                calls & forbidden_calls,
                set(),
                f"{path.name}: {calls & forbidden_calls}",
            )

    def test_store_contains_only_immutable_descriptors(self) -> None:
        store = InMemoryMCPServerStore()
        server = descriptor()

        store.add(server)

        self.assertEqual(store.list_all(), (server,))
        self.assertFalse(hasattr(store, "connections"))
        self.assertFalse(hasattr(store, "transports"))
        self.assertFalse(hasattr(store, "secrets"))
        with self.assertRaises(DescriptorValidationError):
            store.add(object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
