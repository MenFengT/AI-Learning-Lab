import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ResilienceArchitectureTests(unittest.TestCase):
    def test_mcp_client_does_not_import_resilience(self) -> None:
        client_path = PROJECT_ROOT / "app" / "services" / "mcp" / "client.py"
        tree = ast.parse(
            client_path.read_text(encoding="utf-8"), filename=str(client_path)
        )
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        self.assertFalse(any("resilience" in name for name in imports))
        self.assertFalse(any("retry" in name.casefold() for name in imports))
        self.assertFalse(any("circuit" in name.casefold() for name in imports))

    def test_resilience_does_not_depend_on_skills_or_mcp_client(self) -> None:
        resilience_root = PROJECT_ROOT / "app" / "services" / "resilience"
        for path in resilience_root.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("app.skills", source)
            self.assertNotIn("services.mcp.client", source)


if __name__ == "__main__":
    unittest.main()
